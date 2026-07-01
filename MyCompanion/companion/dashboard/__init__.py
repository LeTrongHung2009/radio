"""Dashboard Module - Web-based configuration and monitoring"""

from companion.dashboard.web_configurator import (
    WebConfigurator,
    get_web_configurator,
    initialize_web_configurator
)

__all__ = [
    'WebConfigurator',
    'get_web_configurator',
    'initialize_web_configurator'
]
