"""Identity Module - Core identity management for AI Companion"""

from companion.identity.identity_manager import (
    IdentityManager,
    get_identity_manager,
    initialize_identity_manager
)

__all__ = [
    'IdentityManager',
    'get_identity_manager',
    'initialize_identity_manager'
]
