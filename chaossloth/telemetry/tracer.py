import sentry_sdk
from contextlib import contextmanager

# Optional Sentry Agent Tracing initialization
def init_tracer(dsn: str = ""):
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment="production"
        )

@contextmanager
def trace_span(op: str, description: str):
    try:
        with sentry_sdk.start_span(op=op, description=description) as span:
            yield span
    except Exception:
        yield None
