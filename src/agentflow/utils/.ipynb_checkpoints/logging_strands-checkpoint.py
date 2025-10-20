"""
Logging utilities for AgentFlow with CloudWatch integration
"""

import logging
import sys
import os
from typing import Any, Optional
import structlog
from pythonjsonlogger import jsonlogger

# Try to import watchtower for CloudWatch integration
try:
    import watchtower
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


def setup_logger(name: str, enable_cloudwatch: bool = True) -> structlog.BoundLogger:
    """
    Setup structured logger with JSON formatting and CloudWatch integration
    
    Configures logging for production use with:
    - Structured JSON logging
    - CloudWatch Logs integration (if available)
    - Fault-tolerant configuration
    
    Args:
        name: Logger name
        enable_cloudwatch: Enable CloudWatch logging if available
    
    Returns:
        Configured structlog logger
    """
    
    # Get log level from environment or default to INFO
    log_level_str = os.getenv("AGENTFLOW_LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Add CloudWatch handler if available and enabled
    if CLOUDWATCH_AVAILABLE and enable_cloudwatch:
        cloudwatch_enabled = os.getenv("CLOUDWATCH_ENABLED", "false").lower() == "true"
        if cloudwatch_enabled:
            try:
                log_group = os.getenv("CLOUDWATCH_LOG_GROUP", "/aws/agentflow/production")
                stream_name = os.getenv("CLOUDWATCH_STREAM_NAME", "workflow")
                
                cloudwatch_handler = watchtower.CloudWatchLogHandler(
                    log_group=log_group,
                    stream_name=stream_name,
                    use_queues=True,  # Async logging
                    create_log_group=True
                )
                cloudwatch_handler.setLevel(log_level)
                cloudwatch_handler.setFormatter(CloudWatchFormatter(
                    '%(timestamp)s %(level)s %(logger)s %(message)s'
                ))
                root_logger.addHandler(cloudwatch_handler)
                
                # Log successful CloudWatch setup
                root_logger.info(
                    f"CloudWatch logging enabled: {log_group}/{stream_name}"
                )
            except Exception as e:
                # Fail gracefully if CloudWatch setup fails
                root_logger.warning(
                    f"Failed to setup CloudWatch logging: {str(e)}. "
                    "Continuing with console logging only."
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
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(name)


class CloudWatchFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for CloudWatch Logs
    
    Formats log records as JSON with CloudWatch-compatible fields.
    """
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add AWS-specific fields if available
        if hasattr(record, 'aws_request_id'):
            log_record['aws_request_id'] = record.aws_request_id


def get_cloudwatch_handler(
    log_group: str = "/aws/agentflow/production",
    stream_name: str = "workflow"
) -> Optional[logging.Handler]:
    """
    Get a handler configured for CloudWatch Logs
    
    Args:
        log_group: CloudWatch log group name
        stream_name: CloudWatch log stream name
    
    Returns:
        CloudWatch handler if available, None otherwise
    """
    if not CLOUDWATCH_AVAILABLE:
        return None
    
    try:
        handler = watchtower.CloudWatchLogHandler(
            log_group=log_group,
            stream_name=stream_name,
            use_queues=True,
            create_log_group=True
        )
        formatter = CloudWatchFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
        handler.setFormatter(formatter)
        return handler
    except Exception as e:
        logging.warning(f"Failed to create CloudWatch handler: {str(e)}")
        return None


def get_console_handler() -> logging.Handler:
    """Get a console handler with JSON formatting"""
    handler = logging.StreamHandler(sys.stdout)
    formatter = CloudWatchFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s'
    )
    handler.setFormatter(formatter)
    return handler
