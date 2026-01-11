"""
Unit tests for OpenTelemetry tracing integration.
"""

import pytest

from app.core.tracing import (
    OTEL_AVAILABLE,
    _NoOpSpan,
    _NoOpSpanContext,
    _NoOpTracer,
    create_span,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    record_exception,
    set_span_attribute,
    set_span_status,
    span_id_ctx,
    trace_function,
    trace_id_ctx,
)


class TestNoOpTracer:
    """Tests for the NoOpTracer fallback when OpenTelemetry is not available."""

    def test_noop_tracer_start_span(self):
        """NoOpTracer.start_span returns NoOpSpan."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)

    def test_noop_tracer_start_as_current_span(self):
        """NoOpTracer.start_as_current_span returns NoOpSpanContext."""
        tracer = _NoOpTracer()
        ctx = tracer.start_as_current_span("test")
        assert isinstance(ctx, _NoOpSpanContext)


class TestNoOpSpan:
    """Tests for the NoOpSpan fallback."""

    def test_set_attribute_does_nothing(self):
        """NoOpSpan.set_attribute is a no-op."""
        span = _NoOpSpan()
        span.set_attribute("key", "value")  # Should not raise

    def test_set_status_does_nothing(self):
        """NoOpSpan.set_status is a no-op."""
        span = _NoOpSpan()
        span.set_status("OK")  # Should not raise

    def test_record_exception_does_nothing(self):
        """NoOpSpan.record_exception is a no-op."""
        span = _NoOpSpan()
        span.record_exception(ValueError("test"))  # Should not raise

    def test_add_event_does_nothing(self):
        """NoOpSpan.add_event is a no-op."""
        span = _NoOpSpan()
        span.add_event("test_event", {"key": "value"})  # Should not raise

    def test_end_does_nothing(self):
        """NoOpSpan.end is a no-op."""
        span = _NoOpSpan()
        span.end()  # Should not raise

    def test_is_recording_returns_false(self):
        """NoOpSpan.is_recording always returns False."""
        span = _NoOpSpan()
        assert span.is_recording() is False


class TestNoOpSpanContext:
    """Tests for the NoOpSpanContext context manager."""

    def test_context_manager_enter(self):
        """NoOpSpanContext.__enter__ returns NoOpSpan."""
        ctx = _NoOpSpanContext()
        with ctx as span:
            assert isinstance(span, _NoOpSpan)

    def test_context_manager_does_not_suppress_exception(self):
        """NoOpSpanContext does not suppress exceptions."""
        ctx = _NoOpSpanContext()
        with pytest.raises(ValueError, match="test error"), ctx:
            raise ValueError("test error")


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_noop_when_disabled(self):
        """get_tracer returns NoOpTracer when OTEL is not initialized."""
        tracer = get_tracer("test")
        # Should work without raising
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)

    def test_get_tracer_with_custom_name(self):
        """get_tracer accepts custom name."""
        tracer = get_tracer("my.custom.tracer")
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)


class TestTraceContext:
    """Tests for trace context functions."""

    def test_get_current_trace_id_without_context(self):
        """get_current_trace_id returns None when no context."""
        trace_id_ctx.set(None)
        trace_id = get_current_trace_id()
        # When OTEL is not available or no span, returns context var value
        assert trace_id is None

    def test_get_current_span_id_without_context(self):
        """get_current_span_id returns None when no context."""
        span_id_ctx.set(None)
        span_id = get_current_span_id()
        assert span_id is None

    def test_trace_id_context_var(self):
        """trace_id_ctx can be set and retrieved."""
        test_trace_id = "abc123"
        token = trace_id_ctx.set(test_trace_id)
        try:
            assert trace_id_ctx.get() == test_trace_id
        finally:
            trace_id_ctx.reset(token)

    def test_span_id_context_var(self):
        """span_id_ctx can be set and retrieved."""
        test_span_id = "def456"
        token = span_id_ctx.set(test_span_id)
        try:
            assert span_id_ctx.get() == test_span_id
        finally:
            span_id_ctx.reset(token)


class TestSetSpanAttribute:
    """Tests for set_span_attribute function."""

    def test_set_span_attribute_without_otel(self):
        """set_span_attribute does not raise when OTEL is unavailable."""
        set_span_attribute("key", "value")  # Should not raise

    def test_set_span_attribute_with_various_types(self):
        """set_span_attribute handles various value types."""
        set_span_attribute("string_attr", "value")
        set_span_attribute("int_attr", 42)
        set_span_attribute("float_attr", 3.14)
        set_span_attribute("bool_attr", True)
        # Should not raise for any type


class TestSetSpanStatus:
    """Tests for set_span_status function."""

    def test_set_span_status_ok(self):
        """set_span_status with OK status does not raise."""
        set_span_status("OK")

    def test_set_span_status_error(self):
        """set_span_status with ERROR status does not raise."""
        set_span_status("ERROR", "Something went wrong")

    def test_set_span_status_unset(self):
        """set_span_status with UNSET status does not raise."""
        set_span_status("UNSET")


class TestRecordException:
    """Tests for record_exception function."""

    def test_record_exception_without_otel(self):
        """record_exception does not raise when OTEL is unavailable."""
        record_exception(ValueError("test error"))


class TestCreateSpan:
    """Tests for create_span context manager."""

    def test_create_span_basic(self):
        """create_span creates a context manager."""
        with create_span("test_span"):
            pass  # Should not raise

    def test_create_span_with_attributes(self):
        """create_span accepts attributes."""
        with create_span("test_span", attributes={"key": "value"}):
            pass

    def test_create_span_with_kind(self):
        """create_span accepts different span kinds."""
        for kind in ["internal", "server", "client", "producer", "consumer"]:
            with create_span(f"test_{kind}", kind=kind):
                pass

    def test_create_span_propagates_exception(self):
        """create_span propagates exceptions."""
        with pytest.raises(ValueError, match="test error"), create_span("failing_span"):
            raise ValueError("test error")


class TestTraceFunction:
    """Tests for trace_function decorator."""

    def test_trace_function_sync(self):
        """trace_function works with sync functions."""

        @trace_function()
        def sync_func():
            return "result"

        result = sync_func()
        assert result == "result"

    def test_trace_function_with_args(self):
        """trace_function preserves function arguments."""

        @trace_function()
        def func_with_args(a, b, c=None):
            return a + b + (c or 0)

        result = func_with_args(1, 2, c=3)
        assert result == 6

    def test_trace_function_with_custom_name(self):
        """trace_function accepts custom span name."""

        @trace_function("custom_span_name")
        def func():
            return "result"

        result = func()
        assert result == "result"

    def test_trace_function_with_attributes(self):
        """trace_function accepts custom attributes."""

        @trace_function("span_with_attrs", {"component": "test"})
        def func():
            return "result"

        result = func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_trace_function_async(self):
        """trace_function works with async functions."""

        @trace_function()
        async def async_func():
            return "async_result"

        result = await async_func()
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_trace_function_async_with_args(self):
        """trace_function preserves async function arguments."""

        @trace_function()
        async def async_func_with_args(a, b):
            return a * b

        result = await async_func_with_args(3, 4)
        assert result == 12

    def test_trace_function_preserves_exception(self):
        """trace_function preserves exceptions from decorated function."""

        @trace_function()
        def failing_func():
            raise ValueError("expected error")

        with pytest.raises(ValueError, match="expected error"):
            failing_func()

    @pytest.mark.asyncio
    async def test_trace_function_async_preserves_exception(self):
        """trace_function preserves exceptions from async decorated function."""

        @trace_function()
        async def async_failing_func():
            raise ValueError("expected async error")

        with pytest.raises(ValueError, match="expected async error"):
            await async_failing_func()


class TestOtelAvailability:
    """Tests related to OpenTelemetry availability."""

    def test_otel_available_is_boolean(self):
        """OTEL_AVAILABLE is a boolean."""
        assert isinstance(OTEL_AVAILABLE, bool)

    def test_fallback_when_otel_unavailable(self):
        """Application works when OpenTelemetry is not installed."""
        # All functions should work without raising
        get_tracer()
        get_current_trace_id()
        get_current_span_id()
        set_span_attribute("key", "value")
        set_span_status("OK")
        record_exception(ValueError("test"))

        with create_span("test"):
            pass

        @trace_function()
        def test_func():
            return True

        assert test_func() is True


class TestTraceFunctionReturnTypes:
    """Tests for trace_function return type preservation."""

    def test_trace_function_returns_none(self):
        """trace_function handles None return."""

        @trace_function()
        def func_returns_none():
            pass

        result = func_returns_none()
        assert result is None

    def test_trace_function_returns_list(self):
        """trace_function handles list return."""

        @trace_function()
        def func_returns_list():
            return [1, 2, 3]

        result = func_returns_list()
        assert result == [1, 2, 3]

    def test_trace_function_returns_dict(self):
        """trace_function handles dict return."""

        @trace_function()
        def func_returns_dict():
            return {"key": "value"}

        result = func_returns_dict()
        assert result == {"key": "value"}

    def test_trace_function_returns_tuple(self):
        """trace_function handles tuple return."""

        @trace_function()
        def func_returns_tuple():
            return (1, "two", 3.0)

        result = func_returns_tuple()
        assert result == (1, "two", 3.0)


class TestNestedSpans:
    """Tests for nested span creation."""

    def test_nested_create_span(self):
        """Nested create_span calls work correctly."""
        with create_span("outer"), create_span("inner"):
            pass

    def test_deeply_nested_spans(self):
        """Deeply nested spans work correctly."""
        with (
            create_span("level1"),
            create_span("level2"),
            create_span("level3"),
            create_span("level4"),
        ):
            pass

    def test_nested_trace_function(self):
        """Nested trace_function decorated functions work."""

        @trace_function()
        def outer():
            return inner()

        @trace_function()
        def inner():
            return "result"

        result = outer()
        assert result == "result"


class TestSpanKinds:
    """Tests for different span kinds."""

    def test_internal_span(self):
        """Internal span kind works."""
        with create_span("internal_span", kind="internal"):
            pass

    def test_server_span(self):
        """Server span kind works."""
        with create_span("server_span", kind="server"):
            pass

    def test_client_span(self):
        """Client span kind works."""
        with create_span("client_span", kind="client"):
            pass

    def test_producer_span(self):
        """Producer span kind works."""
        with create_span("producer_span", kind="producer"):
            pass

    def test_consumer_span(self):
        """Consumer span kind works."""
        with create_span("consumer_span", kind="consumer"):
            pass

    def test_unknown_span_kind_defaults_to_internal(self):
        """Unknown span kind defaults to internal."""
        with create_span("unknown_kind", kind="unknown"):
            pass  # Should not raise
