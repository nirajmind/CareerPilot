import logging
from app.api.config import LOG_LEVEL

def setup_logger():
    logger = logging.getLogger("careerpilot")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    return logger
