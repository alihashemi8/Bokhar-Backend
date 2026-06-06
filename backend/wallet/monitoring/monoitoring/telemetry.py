from opentelemetry import trace

tracer = trace.get_tracer(
    "payment-service"
)