import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from datetime import datetime
from app.api.config import LOG_LEVEL

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON Formatter to inject OpenTelemetry trace_id and span_id.
    """
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Inject OpenTelemetry Context
        span = trace.get_current_span()
        if span != trace.INVALID_SPAN:
            ctx = span.get_span_context()
            log_record['trace_id'] = trace.format_trace_id(ctx.trace_id)
            log_record['span_id'] = trace.format_span_id(ctx.span_id)
            
        # Add standard fields if key is missing
        if not log_record.get('timestamp'):
            # Use ISO format for timestamp
            log_record['timestamp'] = datetime.utcnow().isoformat() + "Z" if 'datetime' in globals() else record.asctime
            
        if not log_record.get('level'):
            log_record['level'] = record.levelname
            
        if not log_record.get('logger_name'):
            log_record['logger_name'] = record.name

def setup_logger():
    """
    Configure the application logger with JSON formatting and Trace ID injection.
    """
    logger = logging.getLogger("careerpilot")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Clear existing handlers to prevent duplicates on reload
    if logger.handlers:
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    
    # Define the fields we want in the JSON output via format string
    # Note: python-json-logger parses these fields from the record
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(trace_id)s %(span_id)s'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
