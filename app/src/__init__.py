"""
AI-Assistant Source Package
Core modules for AI-Assistant services
"""


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == 'utils':
        from . import utils
        return utils
    elif name == 'security':
        from . import security
        return security
    elif name == 'database':
        from . import database
        return database
    elif name == 'cache':
        from . import cache
        return cache
    elif name == 'health':
        from . import health
        return health
    elif name == 'errors':
        from . import errors
        return errors
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'utils', 
    'security', 
    'database', 
    'cache', 
    'health',
    'errors'
]
