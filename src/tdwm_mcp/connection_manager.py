"""
Connection Manager for TDWM MCP Server

Handles database connections with automatic retry, connection pooling, and health monitoring.
"""

import asyncio
import logging
import time
from typing import Optional
from .tdsql import TDConn, obfuscate_password

logger = logging.getLogger(__name__)


class TeradataConnectionManager:
    """
    Manages Teradata database connections with retry logic and connection pooling.
    """
    
    def __init__(
        self,
        database_url: str,
        db_name: str,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0
    ):
        self.database_url = database_url
        self.db_name = db_name
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        
        self._connection: Optional[TDConn] = None
        self._connection_lock = asyncio.Lock()
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
        
    async def _create_connection(self) -> TDConn:
        """Create a new database connection."""
        logger.info(f"Creating new database connection to {obfuscate_password(self.database_url)}")
        
        connection = TDConn(self.database_url)
        query_band_string = "ApplicationName=TDWM_MCP;"

        set_query_band_sql = f"SET QUERY_BAND = '{query_band_string}' UPDATE FOR SESSION;"

        cur = connection.cursor()
        cur.execute(set_query_band_sql)
        
        logger.info("Successfully created database connection")
        return connection
        
    async def _is_connection_healthy(self, connection: TDConn) -> bool:
        """Check if the connection is healthy."""
        try:
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False
    
    async def _close_connection(self, connection: TDConn):
        """Close a database connection."""
        try:
            if connection:
                connection.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    async def ensure_connection(self) -> TDConn:
        """
        Ensure we have a healthy database connection, creating one if necessary.
        
        Returns:
            TDConn: A healthy database connection
            
        Raises:
            ConnectionError: If unable to establish a connection after retries
        """
        async with self._connection_lock:
            current_time = time.time()
            
            # Check if we need to perform a health check
            if (self._connection and 
                current_time - self._last_health_check < self._health_check_interval):
                return self._connection
            
            # Perform health check if connection exists
            if self._connection:
                if await self._is_connection_healthy(self._connection):
                    self._last_health_check = current_time
                    return self._connection
                else:
                    logger.warning("Existing connection is unhealthy, closing it")
                    await self._close_connection(self._connection)
                    self._connection = None
            
            # Create new connection with retry logic
            backoff = self.initial_backoff
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    self._connection = await self._create_connection()
                    self._last_health_check = current_time
                    logger.info(f"Database connection established successfully on attempt {attempt + 1}")
                    return self._connection
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Connection attempt {attempt + 1} failed: {obfuscate_password(str(e))}"
                    )
                    
                    if attempt < self.max_retries - 1:
                        logger.info(f"Waiting {backoff} seconds before retry...")
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)
            
            # All attempts failed
            error_msg = f"Failed to establish database connection after {self.max_retries} attempts"
            if last_exception:
                error_msg += f". Last error: {obfuscate_password(str(last_exception))}"
            
            logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def close(self):
        """Close the connection manager and all connections."""
        async with self._connection_lock:
            if self._connection:
                await self._close_connection(self._connection)
                self._connection = None
                
    def get_connection_info(self) -> dict:
        """Get information about the current connection state."""
        return {
            "database_url": obfuscate_password(self.database_url),
            "db_name": self.db_name,
            "has_connection": self._connection is not None,
            "last_health_check": self._last_health_check,
            "health_check_interval": self._health_check_interval,
            "max_retries": self.max_retries
        }