from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind, Tracer

from app.core.config import get_settings

_SETTINGS = get_settings()
_TRACING_CONFIGURED = False


def configure_tracing() -> None:
    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED or not _SETTINGS.otel_enabled:
        return

    resource = Resource.create({"service.name": _SETTINGS.otel_service_name})
    provider = TracerProvider(resource=resource)

    if _SETTINGS.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=_SETTINGS.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _TRACING_CONFIGURED = True


def get_tracer(name: str) -> Tracer:
    return trace.get_tracer(name)


@contextmanager
def traced_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Generator[Span, None, None]:
    tracer = get_tracer("leadline")
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span
