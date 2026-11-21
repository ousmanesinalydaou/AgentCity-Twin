"""OTLP export and lightweight metrics for API and worker processes."""

import os

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import enabled


def initialize(component):
    if not enabled("OTEL_ENABLED"):
        return
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", f"agentcity-{component}")})
    tracer = TracerProvider(resource=resource)
    tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer)
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())])
    )


meter = metrics.get_meter("agentcity")
http_requests = meter.create_counter("agentcity.http.requests")
http_latency = meter.create_histogram("agentcity.http.duration", unit="ms")
run_events = meter.create_counter("agentcity.run.events")
tracer = trace.get_tracer("agentcity")
