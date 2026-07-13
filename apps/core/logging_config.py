"""Structured logging configuration for SGHL."""
import logging
import json
import uuid
from pythonjsonlogger import jsonlogger
from django.conf import settings


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context fields."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = self.formatTime(record)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


class RequestIdFilter(logging.Filter):
    """Add request_id to all log records for correlation."""

    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = str(uuid.uuid4())[:8]
        return True


class RequestIdMiddleware:
    """Middleware to assign a unique request ID to each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.id = str(uuid.uuid4())[:8]

        response = self.get_response(request)

        # Add request ID to response headers for tracing
        response['X-Request-ID'] = request.id

        return response


def setup_logging():
    """Configure structured JSON logging."""
    logger = logging.getLogger()

    # Clear existing handlers
    logger.handlers = []

    formatter = StructuredFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )

    # Console handler - JSON format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())
    logger.addHandler(console_handler)

    # File handler - JSON format
    if not settings.DEBUG:
        file_handler = logging.FileHandler(settings.BASE_DIR / 'logs' / 'sghl.log')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        logger.addHandler(file_handler)

    # Set logging levels
    if settings.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger('django.db.backends').setLevel(logging.WARNING)
    logging.getLogger('django.request').setLevel(logging.INFO)
    logging.getLogger('channels').setLevel(logging.INFO)

    return logger
