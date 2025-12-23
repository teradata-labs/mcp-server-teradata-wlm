"""
Protected Resource Metadata Handler (RFC 9728)
Provides OAuth 2.1 protected resource metadata endpoint for discovery.
"""

from typing import Dict, List, Any
import logging
from .config import OAuthConfig

logger = logging.getLogger(__name__)


class ProtectedResourceMetadata:
    """Handler for OAuth Protected Resource Metadata (RFC 9728)."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Generate protected resource metadata per RFC 9728.
        
        Returns metadata that describes this protected resource,
        including authorization server information and scopes.
        """
        if not self.config.enabled:
            return {}
        
        metadata = {
            # RFC 9728 required fields
            "resource": self.config.resource_server_url,
            "authorization_servers": [
                self.config.get_issuer_url()
            ],
            
            # Keycloak-specific authorization server metadata
            "authorization_server_metadata_endpoints": {
                self.config.get_issuer_url(): self.config.authorization_server_metadata_url
            },
            
            # OpenID Connect Discovery (common for Keycloak)
            "openid_configuration_endpoints": {
                self.config.get_issuer_url(): self.config.openid_configuration_url
            },
            
            # Supported scopes
            "scopes_supported": [
                "tdwm:read",          # Read access to TDWM resources
                "tdwm:write",         # Write access to TDWM resources  
                "tdwm:admin",         # Administrative access
                "tdwm:query",         # Execute queries
                "tdwm:monitor",       # Monitoring operations
                "tdwm:workload",      # Workload management
                "openid",             # OpenID Connect
                "profile",            # Profile information
                "email"               # Email access
            ],
            
            # Token validation information
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "client_secret_jwt",
                "private_key_jwt"
            ],
            
            # Supported grant types
            "grant_types_supported": [
                "authorization_code",
                "client_credentials",
                "refresh_token"
            ],
            
            # Response types supported
            "response_types_supported": [
                "code"
            ],
            
            # Token types
            "token_types_supported": [
                "Bearer"
            ],
            
            # PKCE support (required for OAuth 2.1)
            "code_challenge_methods_supported": [
                "S256"
            ],
            
            # Introspection endpoint
            "introspection_endpoint": self.config.token_validation_endpoint,
            "introspection_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post"
            ],
            
            # JWKS endpoint for JWT validation
            "jwks_uri": self.config.jwks_endpoint,
            
            # Additional TDWM MCP specific metadata
            "mcp_server": {
                "name": "tdwm-mcp",
                "version": "0.1.0",
                "capabilities": [
                    "session_monitoring",
                    "workload_management", 
                    "resource_monitoring",
                    "query_analysis",
                    "tasm_statistics",
                    "dynamic_resources"
                ]
            },
            
            # Security requirements
            "require_request_uri_registration": False,
            "require_signed_request_object": False,
            "mtls_endpoint_aliases": {},
            
            # Client registration
            "registration_endpoint": f"{self.config.get_issuer_url()}/clients-registrations/openid-connect",
            
            # Service documentation
            "service_documentation": "https://github.com/arturborycki/tdwm-mcp",
            
            # RFC 9728 optional fields
            "resource_documentation": "https://github.com/arturborycki/tdwm-mcp/blob/main/README.md"
        }
        
        # Add required scopes if configured
        if self.config.required_scopes:
            metadata["scopes_required"] = self.config.required_scopes
        
        # Add audience validation info
        if self.config.validate_audience:
            metadata["audience"] = self.config.resource_server_url
        
        logger.debug(f"Generated protected resource metadata for {self.config.resource_server_url}")
        return metadata
    
    def get_scopes_for_operation(self, operation_type: str) -> List[str]:
        """
        Get required scopes for different MCP operations.
        
        Args:
            operation_type: Type of operation ('read', 'write', 'admin', 'query', 'monitor')
            
        Returns:
            List of required scopes for the operation
        """
        scope_mapping = {
            'read': ['tdwm:read'],
            'write': ['tdwm:write', 'tdwm:read'], 
            'admin': ['tdwm:admin'],
            'query': ['tdwm:query', 'tdwm:read'],
            'monitor': ['tdwm:monitor', 'tdwm:read'],
            'workload': ['tdwm:workload', 'tdwm:admin'],
            'list': ['tdwm:read'],
            'show': ['tdwm:read'],
            'execute': ['tdwm:query', 'tdwm:read'],
            'manage': ['tdwm:admin']
        }
        
        return scope_mapping.get(operation_type.lower(), ['tdwm:read'])
    
    def validate_scopes_for_tool(self, tool_name: str, user_scopes: List[str]) -> bool:
        """
        Validate if user has required scopes for a specific tool.
        
        Args:
            tool_name: Name of the MCP tool being accessed
            user_scopes: Scopes present in the user's token
            
        Returns:
            True if user has sufficient scopes, False otherwise
        """
        # Map tool names to operation types
        tool_operation_mapping = {
            # Session monitoring tools
            'show_sessions': 'read',
            'show_sql_steps_for_session': 'read',
            'show_sql_text_for_session': 'read',
            'monitor_session_query_band': 'monitor',
            
            # System monitoring tools
            'monitor_amp_load': 'monitor',
            'monitor_awt': 'monitor', 
            'monitor_config': 'monitor',
            'show_physical_resources': 'read',
            
            # Workload management tools
            'list_active_WD': 'read',
            'list_WD': 'read',
            'show_tdwm_summary': 'read',
            'list_delayed_request': 'read',
            'display_delay_queue': 'read',
            'show_trottle_statistics': 'read',
            'list_query_band': 'read',
            
            # Administrative tools
            'abort_sessions_user': 'admin',
            'abort_delayed_request': 'admin',
            'release_delay_queue': 'admin',
            'create_filter_rule': 'admin',
            'add_class_criteria': 'admin',
            'enable_filter_in_default': 'admin',
            'enable_filter_rule': 'admin',
            'activate_rulset': 'admin',
            
            # Query and analysis tools
            'show_query_log': 'query',
            'show_top_users': 'query',
            'show_sw_event_log': 'read',
            'show_tasm_statistics': 'monitor',
            'show_tasm_even_history': 'read',
            'show_tasm_rule_history_red': 'read',
            
            # System information tools
            'identify_blocking': 'read',
            'list_utility_stats': 'read',
            'show_cod_limits': 'read',
            'tdwm_list_clasification': 'read',
        }
        
        operation_type = tool_operation_mapping.get(tool_name, 'read')
        required_scopes = self.get_scopes_for_operation(operation_type)
        
        # Check if user has any of the required scopes
        return any(scope in user_scopes for scope in required_scopes)