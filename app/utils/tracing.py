"""
OpenTelemetry Setup Module.
"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from app.utils.logger import setup_logger

logger = setup_logger()

def setup_tracing(service_name: str, otlp_endpoint: str):
    """
    Configure OpenTelemetry with OTLP exporter.
    """
    logger.info(f"Setting up OpenTelemetry tracing for {service_name} at {otlp_endpoint}")

    resource = Resource.create(attributes={
        SERVICE_NAME: service_name
    })

    provider = TracerProvider(resource=resource)
    
    # Configure OTLP Exporter (gRPC)
    try:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Set global provider
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing configured successfully.")
        
    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry: {e}")
