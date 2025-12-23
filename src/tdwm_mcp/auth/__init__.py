"""
OAuth 2.1 Authentication Module for TDWM MCP Server
"""

from .config import OAuthConfig
from .metadata import ProtectedResourceMetadata
from .middleware import OAuthMiddleware, TokenClaims, TokenValidationError
from .endpoints import OAuthEndpoints

__all__ = [
    'OAuthConfig', 
    'ProtectedResourceMetadata', 
    'OAuthMiddleware', 
    'TokenClaims', 
    'TokenValidationError',
    'OAuthEndpoints'
]