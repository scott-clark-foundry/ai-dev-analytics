"""Logging configuration and error handling for telemetry processing."""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration for the telemetry consumer."""
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('devai_analytics')
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler for {log_file}: {e}")
    
    return logger


class TelemetryError(Exception):
    """Base exception for telemetry processing errors."""
    pass


class ReceiverError(TelemetryError):
    """Error in OTLP receiver operations."""
    pass


class ProcessorError(TelemetryError):
    """Error in telemetry data processing."""
    pass


class StorageError(TelemetryError):
    """Error in data storage operations."""
    pass


def handle_telemetry_error(func):
    """Decorator to handle telemetry processing errors gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TelemetryError as e:
            logger = logging.getLogger('devai_analytics')
            logger.error(f"Telemetry error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger = logging.getLogger('devai_analytics')
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise TelemetryError(f"Unexpected error: {e}") from e
    
    return wrapper