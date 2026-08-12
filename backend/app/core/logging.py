import logging
import structlog
import sys
from app.core.request_context import get_context_dict

def add_context_vars(logger, method_name, event_dict):
    """Adds ContextVars to the structlog event dictionary."""
    ctx = get_context_dict()
    event_dict.update(ctx)
    return event_dict

def setup_logging():
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            add_context_vars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
def get_logger(name: str):
    return structlog.get_logger(name)
