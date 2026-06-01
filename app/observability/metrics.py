from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

api_requests_total = Counter(
    "leadline_api_requests_total",
    "Total API requests",
    ["path", "method", "status_code", "tenant_id"],
)
api_request_latency_ms = Histogram(
    "leadline_api_request_latency_ms",
    "API request latency in milliseconds",
    ["path", "method"],
)

queue_publish_total = Counter(
    "leadline_queue_publish_total",
    "Queue publish outcomes",
    ["queue_name", "outcome"],
)

ai_calls_total = Counter(
    "leadline_ai_calls_total",
    "AI call outcomes",
    ["model", "outcome"],
)

integration_calls_total = Counter(
    "leadline_integration_calls_total",
    "Integration call outcomes",
    ["provider", "operation", "outcome"],
)

business_kpi_events_total = Counter(
    "leadline_business_kpi_events_total",
    "Business KPI events",
    ["event", "tenant_id"],
)


def render_metrics() -> tuple[bytes, str]:
    payload = generate_latest()
    return payload, CONTENT_TYPE_LATEST
