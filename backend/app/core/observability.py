"""
Observability utilities for monitoring and metrics.

Provides:
- Prometheus metrics export
- Health check endpoints
- Request tracking
- Performance monitoring
"""

import time
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

openai_requests_total = Counter(
    'openai_requests_total',
    'Total OpenAI API requests',
    ['model', 'status']
)

openai_tokens_total = Counter(
    'openai_tokens_total',
    'Total OpenAI tokens used',
    ['model', 'type']  # type: prompt or completion
)

openai_request_duration_seconds = Histogram(
    'openai_request_duration_seconds',
    'OpenAI API request duration in seconds',
    ['model']
)

rag_searches_total = Counter(
    'rag_searches_total',
    'Total RAG search operations',
    ['status']
)

rag_search_duration_seconds = Histogram(
    'rag_search_duration_seconds',
    'RAG search duration in seconds'
)

tasks_created_total = Counter(
    'tasks_created_total',
    'Total tasks created',
    ['task_type']
)

tasks_completed_total = Counter(
    'tasks_completed_total',
    'Total tasks completed',
    ['task_type', 'status']
)

tasks_in_queue = Gauge(
    'tasks_in_queue',
    'Number of tasks in queue',
    ['state']
)

webhook_events_total = Counter(
    'webhook_events_total',
    'Total webhook events received',
    ['source', 'event_type']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.
    
    Tracks:
    - Request count by method, endpoint, status
    - Request duration
    - Requests in progress
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for /metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Time the request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            # Track errors
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            logger.error(f"Request failed: {method} {endpoint}: {e}")
            raise
        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
            
            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        # Track request completion
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        return response


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app) -> None:
    """
    Configure metrics collection for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add metrics endpoint
    app.add_route("/metrics", metrics_endpoint)
    
    logger.info("Prometheus metrics configured at /metrics")


# Utility functions for tracking custom metrics

def track_openai_request(model: str, status: str, duration: float) -> None:
    """Track OpenAI API request."""
    openai_requests_total.labels(model=model, status=status).inc()
    openai_request_duration_seconds.labels(model=model).observe(duration)


def track_openai_tokens(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Track OpenAI token usage."""
    openai_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
    openai_tokens_total.labels(model=model, type="completion").inc(completion_tokens)


def track_rag_search(status: str, duration: float) -> None:
    """Track RAG search operation."""
    rag_searches_total.labels(status=status).inc()
    rag_search_duration_seconds.observe(duration)


def track_task(task_type: str, state: str) -> None:
    """Track task creation or completion."""
    if state == "pending":
        tasks_created_total.labels(task_type=task_type).inc()
    elif state in ["done", "failed"]:
        tasks_completed_total.labels(task_type=task_type, status=state).inc()


def update_task_queue_gauge(pending: int, in_progress: int, failed: int) -> None:
    """Update task queue gauges."""
    tasks_in_queue.labels(state="pending").set(pending)
    tasks_in_queue.labels(state="in_progress").set(in_progress)
    tasks_in_queue.labels(state="failed").set(failed)


def track_webhook(source: str, event_type: str) -> None:
    """Track webhook event."""
    webhook_events_total.labels(source=source, event_type=event_type).inc()
