"""
PocketPlot Universe - Sentry integration (v24).

Opt-in error tracking. Activates only when SENTRY_DSN env var is set.
On activation, wraps the Flask app + reports unhandled exceptions + slow requests.

Usage:
  import sentry_v24
  sentry_v24.init(app)

Safe to call multiple times. Falls through silently if not configured.
"""
import os


def init(app, *, dsn_env='SENTRY_DSN', environment='production'):
    """Initialize Sentry for the Flask app if DSN is set."""
    dsn = os.environ.get(dsn_env)
    if not dsn:
        # Not configured - silent no-op
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        # sentry-sdk not installed - silent no-op
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
        traces_sample_rate=0.1,           # 10% of requests for performance
        profiles_sample_rate=0.1,         # 10% for profiling
        send_default_pii=False,           # don't send user PII automatically
        release=os.environ.get('POCKETPLOT_RELEASE', 'pocketplot-unknown'),
    )
    return True


def capture_exception(exc, **context):
    """Capture an exception with optional context. No-op if not configured."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def capture_message(msg, level='info', **context):
    """Capture a message. No-op if not configured."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_message(msg, level=level)
    except Exception:
        pass
