import logging
from pathlib import Path

_LOGGER_NAME = "smart_syllabus"


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s layer=%(layer)s request_id=%(request_id)s %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(request_id: str, layer: str, message: str) -> None:
    logging.getLogger(_LOGGER_NAME).info(
        message,
        extra={"request_id": request_id, "layer": layer},
    )
