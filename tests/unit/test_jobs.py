"""
Tests for background job system.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.jobs import enqueue, enqueue_in
from app.jobs.decorators import RetryConfig, background_task, retry, timeout
from app.jobs.email_jobs import (
    send_notification_email,
    send_password_reset_email,
    send_welcome_email,
)
from app.jobs.report_jobs import cleanup_old_data, export_user_data, generate_daily_report
from app.jobs.worker import WorkerSettings, get_redis_settings


class TestWorkerConfig:
    """Tests for ARQ worker configuration."""

    def test_worker_settings_has_functions(self):
        """WorkerSettings should have job functions configured."""
        assert hasattr(WorkerSettings, "functions")
        assert len(WorkerSettings.functions) > 0

    def test_worker_settings_has_cron_jobs(self):
        """WorkerSettings should have cron jobs configured."""
        assert hasattr(WorkerSettings, "cron_jobs")
        assert len(WorkerSettings.cron_jobs) > 0

    def test_worker_settings_has_lifecycle_hooks(self):
        """WorkerSettings should have startup/shutdown hooks."""
        assert hasattr(WorkerSettings, "on_startup")
        assert hasattr(WorkerSettings, "on_shutdown")
        assert callable(WorkerSettings.on_startup)
        assert callable(WorkerSettings.on_shutdown)

    def test_worker_settings_default_values(self):
        """WorkerSettings should have sensible defaults."""
        assert WorkerSettings.max_jobs == 10
        assert WorkerSettings.job_timeout == 300
        assert WorkerSettings.keep_result == 3600
        assert WorkerSettings.poll_delay == 0.5

    def test_get_redis_settings_no_url(self):
        """get_redis_settings should return None when no URL configured."""
        with patch("app.jobs.worker.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            result = get_redis_settings()
            assert result is None

    def test_get_redis_settings_with_url(self):
        """get_redis_settings should parse Redis URL correctly."""
        with patch("app.jobs.worker.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/1"
            result = get_redis_settings()
            assert result is not None
            assert result.host == "localhost"
            assert result.port == 6379
            assert result.database == 1


class TestEnqueue:
    """Tests for job enqueue functionality."""

    @pytest.mark.asyncio
    async def test_enqueue_without_redis_executes_sync(self):
        """Without Redis, jobs should execute synchronously."""
        with patch("app.jobs.get_redis_settings", return_value=None):
            # Reset pool
            import app.jobs

            app.jobs._pool = None

            # This should execute the job synchronously
            result = await enqueue(
                "app.jobs.email_jobs.send_welcome_email",
                "test@example.com",
                "Test User",
            )
            # The job should have executed (no exception)
            assert result is None  # send_welcome_email returns None

    @pytest.mark.asyncio
    async def test_enqueue_in_defers_job(self):
        """enqueue_in should defer job execution."""
        with patch("app.jobs.enqueue") as mock_enqueue:
            mock_enqueue.return_value = "job-123"
            await enqueue_in(
                "app.jobs.email_jobs.send_welcome_email",
                60,  # defer by 60 seconds
                "test@example.com",
                "Test User",
            )
            mock_enqueue.assert_called_once()
            call_kwargs = mock_enqueue.call_args[1]
            assert call_kwargs["_defer_by"] == 60


class TestEmailJobs:
    """Tests for email job functions."""

    @pytest.mark.asyncio
    async def test_send_welcome_email(self, caplog):
        """send_welcome_email should log the email details."""
        await send_welcome_email({}, "user@example.com", "John Doe")
        assert "Welcome email sent to user@example.com" in caplog.text

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, caplog):
        """send_password_reset_email should log the email details."""
        await send_password_reset_email(
            {}, "user@example.com", "https://example.com/reset/abc123"
        )
        assert "Password reset email sent to user@example.com" in caplog.text

    @pytest.mark.asyncio
    async def test_send_notification_email(self, caplog):
        """send_notification_email should log the email details."""
        await send_notification_email(
            {},
            "user@example.com",
            "Test Subject",
            "Test body content",
        )
        assert "Notification email sent to user@example.com" in caplog.text


class TestReportJobs:
    """Tests for report job functions."""

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, session, caplog):
        """generate_daily_report should generate a report dict."""
        # Patch the session context to use our test session
        with patch("app.jobs.report_jobs.get_session_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await generate_daily_report({})

            assert "date" in result
            assert "total_users" in result
            assert "active_users_24h" in result
            assert "new_users_today" in result
            assert "Daily report generated" in caplog.text

    @pytest.mark.asyncio
    async def test_export_user_data_not_found(self, caplog):
        """export_user_data should return error for non-existent user."""
        # Create a mock context manager that returns a session with no user
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        @asynccontextmanager
        async def mock_session_context():
            # Create a mock result that returns None (not a coroutine)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None

            # Session execute must be async but return the sync mock_result
            mock_session = MagicMock()

            async def async_execute(*args, **kwargs):
                return mock_result

            mock_session.execute = async_execute
            yield mock_session

        with patch(
            "app.jobs.report_jobs.get_session_context",
            mock_session_context,
        ):
            result = await export_user_data({}, "00000000-0000-0000-0000-000000000000")
            assert result == {"error": "User not found"}
            assert "not found for data export" in caplog.text

    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, caplog):
        """cleanup_old_data should return cleanup summary."""
        result = await cleanup_old_data({})

        assert "executed_at" in result
        assert "deleted_records" in result
        assert "archived_records" in result
        assert "freed_storage_mb" in result
        assert "Data cleanup complete" in caplog.text


class TestDecorators:
    """Tests for job decorators."""

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """retry should not retry on success."""
        call_count = 0

        @retry(RetryConfig(max_attempts=3))
        async def success_job():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_job()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_decorator_retries_on_failure(self):
        """retry should retry on failure."""
        call_count = 0

        @retry(RetryConfig(max_attempts=3, initial_delay=0.01))
        async def flaky_job():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await flaky_job()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_max_attempts_exceeded(self):
        """retry should raise after max attempts."""
        call_count = 0

        @retry(RetryConfig(max_attempts=3, initial_delay=0.01))
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_decorator_success(self):
        """timeout should allow fast jobs to complete."""

        @timeout(1.0)
        async def fast_job():
            await asyncio.sleep(0.01)
            return "done"

        result = await fast_job()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_timeout_decorator_timeout(self):
        """timeout should raise on slow jobs."""

        @timeout(0.05)
        async def slow_job():
            await asyncio.sleep(1.0)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await slow_job()

    @pytest.mark.asyncio
    async def test_background_task_decorator(self):
        """background_task should combine retry and timeout."""

        @background_task(max_attempts=2, timeout_seconds=1.0)
        async def my_task():
            return "completed"

        result = await my_task()
        assert result == "completed"
        assert hasattr(my_task, "_is_background_task")
        assert my_task._is_background_task is True
        assert my_task._max_attempts == 2
        assert my_task._timeout_seconds == 1.0
