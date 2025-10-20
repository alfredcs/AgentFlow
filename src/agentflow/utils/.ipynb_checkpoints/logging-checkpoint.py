"""
Logging utilities for AgentFlow
"""

import logging
import sys
from typing import Any
import structlog
from pythonjsonlogger import jsonlogger


def setup_logger(name: str) -> structlog.BoundLogger:
    """
    Setup structured logger with JSON formatting
    
    Configures logging for production use with CloudWatch compatibility.
    """
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(name)


class CloudWatchFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for CloudWatch Logs"""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def get_cloudwatch_handler() -> logging.Handler:
    """Get a handler configured for CloudWatch Logs"""
    handler = logging.StreamHandler(sys.stdout)
    formatter = CloudWatchFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s'
    )
    handler.setFormatter(formatter)
    return handler
