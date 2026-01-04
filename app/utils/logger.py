import logging
from app.api.config import LOG_LEVEL

def setup_logger():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("careerpilot")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    return logger