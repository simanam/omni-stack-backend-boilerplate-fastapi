"""
Load Testing with Locust

This file contains load test scenarios for the OmniStack API.

Usage:
    # Install Locust
    pip install locust

    # Run load test (Web UI)
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Run load test (Headless)
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless

    # Run specific user class
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --users 50 --spawn-rate 5 AuthenticatedUser

Performance Targets:
    - P95 response time < 500ms
    - Error rate < 1%
    - Throughput > 100 req/s per instance
"""

import random
import string
from typing import Any

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner

# =============================================================================
# Configuration
# =============================================================================

# Test data
TEST_PROJECTS = [
    {"name": f"Project {i}", "description": f"Load test project {i}"}
    for i in range(100)
]

# Auth tokens for testing (replace with real tokens or generate dynamically)
# In production tests, you would get these from your auth provider
TEST_AUTH_TOKEN = "your-test-jwt-token-here"


def generate_random_string(length: int = 10) -> str:
    """Generate a random string for test data."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# =============================================================================
# Event Handlers
# =============================================================================


@events.init.add_listener
def on_locust_init(environment: Any, **kwargs: Any) -> None:
    """Initialize test environment."""
    if isinstance(environment.runner, MasterRunner):
        print("Running as master node")
    else:
        print("Running as worker node")


@events.test_start.add_listener
def on_test_start(environment: Any, **kwargs: Any) -> None:
    """Called when test starts."""
    print(f"Load test starting against {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment: Any, **kwargs: Any) -> None:
    """Called when test stops."""
    print("Load test completed")


# =============================================================================
# User Classes
# =============================================================================


class PublicUser(HttpUser):
    """
    Simulates unauthenticated users accessing public endpoints.
    These are typically health checks and public information endpoints.
    """

    weight = 1  # Lower weight - fewer public users
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    @task(10)
    def health_check(self) -> None:
        """Check basic health endpoint."""
        with self.client.get(
            "/api/v1/public/health",
            name="/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "healthy":
                    response.failure("Unhealthy status returned")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(5)
    def health_ready(self) -> None:
        """Check readiness endpoint (includes DB/Redis checks)."""
        with self.client.get(
            "/api/v1/public/health/ready",
            name="/health/ready",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                # Service unavailable is expected if dependencies are down
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def metrics(self) -> None:
        """Fetch Prometheus metrics."""
        self.client.get("/api/v1/public/metrics", name="/metrics")


class AuthenticatedUser(HttpUser):
    """
    Simulates authenticated users performing typical API operations.
    This is the primary load test scenario.
    """

    weight = 5  # Higher weight - more authenticated users
    wait_time = between(0.5, 2)  # Faster interactions

    def on_start(self) -> None:
        """Called when user starts - set up auth headers."""
        # In a real test, you would get a valid token from your auth provider
        self.headers = {
            "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }
        self.projects: list[str] = []

    @task(10)
    def get_user_profile(self) -> None:
        """Get current user profile."""
        self.client.get(
            "/api/v1/app/users/me",
            headers=self.headers,
            name="/users/me",
        )

    @task(8)
    def list_projects(self) -> None:
        """List user's projects."""
        with self.client.get(
            "/api/v1/app/projects",
            headers=self.headers,
            name="/projects [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Store project IDs for other operations
                if data.get("items"):
                    self.projects = [p["id"] for p in data["items"]]
                response.success()

    @task(5)
    def create_project(self) -> None:
        """Create a new project."""
        project_data = random.choice(TEST_PROJECTS).copy()
        project_data["name"] = f"{project_data['name']} - {generate_random_string(5)}"

        with self.client.post(
            "/api/v1/app/projects",
            headers=self.headers,
            json=project_data,
            name="/projects [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.projects.append(data["id"])
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized - check auth token")
            else:
                response.failure(f"Status: {response.status_code}")

    @task(6)
    def get_project(self) -> None:
        """Get a specific project."""
        if not self.projects:
            return

        project_id = random.choice(self.projects)
        self.client.get(
            f"/api/v1/app/projects/{project_id}",
            headers=self.headers,
            name="/projects/{id} [GET]",
        )

    @task(3)
    def update_project(self) -> None:
        """Update a project."""
        if not self.projects:
            return

        project_id = random.choice(self.projects)
        update_data = {"description": f"Updated at {generate_random_string(10)}"}

        self.client.patch(
            f"/api/v1/app/projects/{project_id}",
            headers=self.headers,
            json=update_data,
            name="/projects/{id} [PATCH]",
        )

    @task(1)
    def delete_project(self) -> None:
        """Delete a project."""
        if not self.projects:
            return

        project_id = self.projects.pop()
        self.client.delete(
            f"/api/v1/app/projects/{project_id}",
            headers=self.headers,
            name="/projects/{id} [DELETE]",
        )


class BillingUser(HttpUser):
    """
    Simulates users checking billing/subscription status.
    Lower frequency - users don't check billing constantly.
    """

    weight = 1
    wait_time = between(5, 15)

    def on_start(self) -> None:
        """Set up auth headers."""
        self.headers = {
            "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

    @task(5)
    def get_billing_status(self) -> None:
        """Check subscription status."""
        self.client.get(
            "/api/v1/app/billing/status",
            headers=self.headers,
            name="/billing/status",
        )

    @task(2)
    def get_invoices(self) -> None:
        """List invoices."""
        self.client.get(
            "/api/v1/app/billing/invoices",
            headers=self.headers,
            name="/billing/invoices",
        )


class AIUser(HttpUser):
    """
    Simulates users making AI completion requests.
    These are expensive operations with longer response times.
    """

    weight = 1
    wait_time = between(5, 30)  # Longer waits between AI requests

    def on_start(self) -> None:
        """Set up auth headers."""
        self.headers = {
            "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

    @task(3)
    def check_ai_status(self) -> None:
        """Check AI service status."""
        self.client.get(
            "/api/v1/app/ai/status",
            headers=self.headers,
            name="/ai/status",
        )

    @task(1)
    def simple_completion(self) -> None:
        """Request a simple AI completion."""
        # Note: This will actually call the AI provider
        # In load testing, you might want to mock this
        prompts = [
            "What is 2+2?",
            "Say hello in French",
            "What color is the sky?",
        ]

        with self.client.post(
            "/api/v1/app/ai/chat",
            headers=self.headers,
            json={"prompt": random.choice(prompts)},
            name="/ai/chat",
            timeout=30,  # AI requests can be slow
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited - expected under load
                response.success()
            elif response.status_code == 503:
                # AI service unavailable
                response.success()


class FileUser(HttpUser):
    """
    Simulates users working with file uploads.
    """

    weight = 1
    wait_time = between(3, 10)

    def on_start(self) -> None:
        """Set up auth headers."""
        self.headers = {
            "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }
        self.files: list[str] = []

    @task(5)
    def list_files(self) -> None:
        """List user's files."""
        with self.client.get(
            "/api/v1/app/files",
            headers=self.headers,
            name="/files [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    self.files = [f["id"] for f in data["items"]]
                response.success()

    @task(3)
    def request_upload_url(self) -> None:
        """Request a presigned upload URL."""
        self.client.post(
            "/api/v1/app/files/upload-url",
            headers=self.headers,
            json={
                "filename": f"test-{generate_random_string(8)}.txt",
                "content_type": "text/plain",
            },
            name="/files/upload-url",
        )

    @task(2)
    def get_file(self) -> None:
        """Get file metadata."""
        if not self.files:
            return

        file_id = random.choice(self.files)
        self.client.get(
            f"/api/v1/app/files/{file_id}",
            headers=self.headers,
            name="/files/{id} [GET]",
        )


# =============================================================================
# Spike Test Scenario
# =============================================================================


class SpikeUser(HttpUser):
    """
    Simulates sudden traffic spikes.
    Use this to test auto-scaling and rate limiting.

    Run with:
        locust -f tests/load/locustfile.py --host=http://localhost:8000 \
            --users 500 --spawn-rate 100 --run-time 1m SpikeUser
    """

    wait_time = between(0.1, 0.5)  # Very fast requests

    @task
    def rapid_health_check(self) -> None:
        """Rapid-fire health checks."""
        self.client.get("/api/v1/public/health", name="/health [spike]")


# =============================================================================
# Soak Test Scenario
# =============================================================================


class SoakUser(HttpUser):
    """
    Simulates sustained load over extended period.
    Use this to test memory leaks and stability.

    Run with:
        locust -f tests/load/locustfile.py --host=http://localhost:8000 \
            --users 50 --spawn-rate 1 --run-time 1h SoakUser
    """

    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Set up auth headers."""
        self.headers = {
            "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

    @task(5)
    def health_check(self) -> None:
        """Steady health checks."""
        self.client.get("/api/v1/public/health", name="/health [soak]")

    @task(3)
    def profile_check(self) -> None:
        """Regular profile checks."""
        self.client.get(
            "/api/v1/app/users/me",
            headers=self.headers,
            name="/users/me [soak]",
        )

    @task(2)
    def list_projects(self) -> None:
        """Regular project listing."""
        self.client.get(
            "/api/v1/app/projects",
            headers=self.headers,
            name="/projects [soak]",
        )
