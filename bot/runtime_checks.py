"""Startup checks for dependencies and runtime paths."""

from pathlib import Path
import logging
from typing import Iterable, Optional

import pytesseract

from bot.config import RuntimeConfig


def configure_logging(config: RuntimeConfig) -> logging.Logger:
    """Configure logging.

    Parameters:
        config: Parameter containing configuration values that guide behavior.

    Local Variables:
        console_handler: Local variable for console handler used in this routine.
        file_handler: Local variable for file handler used in this routine.
        formatter: Local variable for formatter used in this routine.
        log_file: Local variable for log file used in this routine.
        logger: Local variable used to emit diagnostic log messages.

    Returns:
        A value matching the annotated return type `logging.Logger`.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    config.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = config.log_dir / "bot.log"

    logger = logging.getLogger("python_bot")
    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if config.debug else logging.INFO)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def ensure_directories(paths: Iterable[Path]):
    """Ensure directories.

    Parameters:
        paths: Parameter for paths used in this routine.

    Local Variables:
        path: Local variable for path used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _resolve_tesseract_cmd() -> Optional[str]:
    """Internal helper to resolve tesseract cmd.

    Parameters:
        None.

    Local Variables:
        candidate: Local variable for candidate used in this routine.
        candidates: Local variable for candidates used in this routine.

    Returns:
        A value matching the annotated return type `Optional[str]`.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def run_startup_checks(config: RuntimeConfig, logger: logging.Logger):
    """Run startup checks.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        fallback_cmd: Local variable for fallback cmd used in this routine.
        version: Local variable for version used in this routine.

    Returns:
        None.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    ensure_directories(
        [
            config.log_dir,
            config.perf_report_dir,
            config.screenshot_path,
            config.ocr_dataset_raw_dir,
            config.ocr_dataset_labeled_dir,
            config.pickit_db_path.parent,
            config.observer_output_dir,
            config.observer_image_output_dir,
        ]
    )

    try:
        version = pytesseract.get_tesseract_version()
        logger.info("Detected tesseract version: %s", version)
    except Exception:
        fallback_cmd = _resolve_tesseract_cmd()
        if fallback_cmd:
            pytesseract.pytesseract.tesseract_cmd = fallback_cmd
            version = pytesseract.get_tesseract_version()
            logger.info("Detected tesseract version via fallback path: %s", version)
        else:
            raise RuntimeError(
                "Tesseract OCR is not available. Install Tesseract and ensure it is on PATH."
            )

    if not config.teammate_template_path.exists():
        logger.warning(
            "Template not found at %s. Vision will fall back to color-only teammate detection.",
            config.teammate_template_path,
        )

    if not config.pickit_db_path.exists():
        logger.warning("Pickit database not found at %s. Built-in rules will be used.", config.pickit_db_path)
    else:
        logger.info("Using pickit database: %s", config.pickit_db_path)
