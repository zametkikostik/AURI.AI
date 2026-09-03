"""Sentry + OpenTelemetry bootstrap (optional, env-driven)."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def setup_sentry(app=None) -> bool:
    dsn = getattr(settings, "sentry_dsn", None)
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.app_env,
            traces_sample_rate=float(getattr(settings, "sentry_traces_sample_rate", 0.1) or 0.1),
            profiles_sample_rate=0.0,
            integrations=[
                FastApiIntegration(),
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("sentry_initialized", env=settings.app_env)
        return True
    except Exception as e:
        logger.warning("sentry_init_failed", error=str(e))
        return False


def setup_opentelemetry(app=None) -> bool:
    endpoint = getattr(settings, "otel_exporter_otlp_endpoint", None)
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        resource = Resource.create(
            {
                "service.name": getattr(settings, "otel_service_name", None) or "auri-backend",
                "deployment.environment": settings.app_env,
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()

        logger.info("otel_initialized", endpoint=endpoint)
        return True
    except Exception as e:
        logger.warning("otel_init_failed", error=str(e))
        return False
