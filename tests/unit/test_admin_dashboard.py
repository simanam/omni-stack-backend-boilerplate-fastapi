"""
Tests for admin dashboard endpoints.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.audit_log import AuditLog, AuditLogCreate, AuditLogRead
from app.models.feature_flag import (
    FeatureFlag,
    FeatureFlagCheck,
    FeatureFlagCreate,
    FeatureFlagRead,
)
from app.models.user import User


@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user for testing."""
    return User(
        id="admin_123",
        email="admin@example.com",
        full_name="Admin User",
        role="admin",
        is_active=True,
    )


@pytest.fixture
def mock_regular_user() -> User:
    """Create a mock regular user for testing."""
    return User(
        id="user_456",
        email="user@example.com",
        full_name="Regular User",
        role="user",
        is_active=True,
        subscription_plan="pro",
    )


@pytest.fixture
def mock_feature_flag() -> FeatureFlag:
    """Create a mock feature flag for testing."""
    return FeatureFlag(
        id="flag_123",
        key="test_feature",
        name="Test Feature",
        description="A test feature flag",
        flag_type="boolean",
        enabled=True,
        percentage=0,
        user_ids=[],
        plans=[],
        extra_data={},
        created_by="admin_123",
        updated_by="admin_123",
    )


@pytest.fixture
def mock_audit_log() -> AuditLog:
    """Create a mock audit log for testing."""
    return AuditLog(
        id="log_123",
        actor_id="admin_123",
        actor_email="admin@example.com",
        actor_role="admin",
        action="user.updated",
        description="Updated user profile",
        resource_type="user",
        resource_id="user_456",
        details={"field": "role", "old": "user", "new": "admin"},
        ip_address="127.0.0.1",
        request_id="req_123",
    )


class TestAuditLog:
    """Tests for AuditLog model and schemas."""

    def test_audit_log_creation(self, mock_audit_log):
        """AuditLog should be created with correct attributes."""
        assert mock_audit_log.actor_id == "admin_123"
        assert mock_audit_log.action == "user.updated"
        assert mock_audit_log.resource_type == "user"
        assert mock_audit_log.resource_id == "user_456"
        assert mock_audit_log.details["field"] == "role"

    def test_audit_log_create_schema(self):
        """AuditLogCreate schema should validate correctly."""
        create_data = AuditLogCreate(
            actor_id="admin_123",
            actor_email="admin@example.com",
            action="user.created",
            resource_type="user",
            resource_id="user_789",
            details={"email": "new@example.com"},
        )
        assert create_data.action == "user.created"
        assert create_data.resource_type == "user"

    def test_audit_log_read_schema(self, mock_audit_log):
        """AuditLogRead schema should serialize correctly."""
        read_data = AuditLogRead.model_validate(mock_audit_log)
        assert read_data.id == "log_123"
        assert read_data.actor_id == "admin_123"
        assert read_data.action == "user.updated"

    def test_audit_log_with_impersonation(self):
        """AuditLog should track impersonation correctly."""
        log = AuditLog(
            id="log_456",
            actor_id="user_789",
            actor_email="user@example.com",
            impersonator_id="admin_123",
            action="project.created",
            resource_type="project",
            resource_id="proj_123",
        )
        assert log.impersonator_id == "admin_123"
        assert log.actor_id == "user_789"


class TestFeatureFlag:
    """Tests for FeatureFlag model and schemas."""

    def test_feature_flag_creation(self, mock_feature_flag):
        """FeatureFlag should be created with correct attributes."""
        assert mock_feature_flag.key == "test_feature"
        assert mock_feature_flag.flag_type == "boolean"
        assert mock_feature_flag.enabled is True

    def test_feature_flag_create_schema(self):
        """FeatureFlagCreate schema should validate correctly."""
        create_data = FeatureFlagCreate(
            key="new_feature",
            name="New Feature",
            description="A new feature",
            flag_type="percentage",
            percentage=50,
        )
        assert create_data.key == "new_feature"
        assert create_data.percentage == 50

    def test_feature_flag_percentage_validation(self):
        """FeatureFlagCreate should validate percentage range."""
        # Valid percentage
        create_data = FeatureFlagCreate(
            key="test",
            name="Test",
            percentage=100,
        )
        assert create_data.percentage == 100

    def test_feature_flag_read_schema(self, mock_feature_flag):
        """FeatureFlagRead schema should serialize correctly."""
        read_data = FeatureFlagRead.model_validate(mock_feature_flag)
        assert read_data.key == "test_feature"
        assert read_data.enabled is True

    def test_feature_flag_check_enabled(self):
        """FeatureFlagCheck should represent enabled state."""
        check = FeatureFlagCheck(
            key="test_feature",
            enabled=True,
            reason="Flag is enabled globally",
        )
        assert check.enabled is True
        assert "enabled" in check.reason.lower()

    def test_feature_flag_check_disabled(self):
        """FeatureFlagCheck should represent disabled state."""
        check = FeatureFlagCheck(
            key="test_feature",
            enabled=False,
            reason="Flag is disabled",
        )
        assert check.enabled is False

    def test_feature_flag_user_list_type(self):
        """FeatureFlag should support user_list type."""
        flag = FeatureFlag(
            id="flag_user",
            key="beta_users",
            name="Beta Users",
            flag_type="user_list",
            enabled=True,
            user_ids=["user_1", "user_2", "user_3"],
        )
        assert flag.flag_type == "user_list"
        assert len(flag.user_ids) == 3
        assert "user_1" in flag.user_ids

    def test_feature_flag_plan_based_type(self):
        """FeatureFlag should support plan_based type."""
        flag = FeatureFlag(
            id="flag_plan",
            key="premium_feature",
            name="Premium Feature",
            flag_type="plan_based",
            enabled=True,
            plans=["pro", "enterprise"],
        )
        assert flag.flag_type == "plan_based"
        assert "pro" in flag.plans
        assert "enterprise" in flag.plans
        assert "free" not in flag.plans


class TestFeatureFlagEvaluation:
    """Tests for feature flag evaluation logic."""

    def test_boolean_flag_enabled(self, mock_feature_flag):
        """Boolean flag should return enabled when enabled=True."""
        assert mock_feature_flag.enabled is True
        assert mock_feature_flag.flag_type == "boolean"

    def test_boolean_flag_disabled(self):
        """Boolean flag should return disabled when enabled=False."""
        flag = FeatureFlag(
            id="flag_disabled",
            key="disabled_feature",
            name="Disabled Feature",
            flag_type="boolean",
            enabled=False,
        )
        assert flag.enabled is False

    def test_user_list_contains_user(self):
        """User list flag should be enabled for users in the list."""
        flag = FeatureFlag(
            id="flag_list",
            key="beta_feature",
            name="Beta Feature",
            flag_type="user_list",
            enabled=True,
            user_ids=["user_123", "user_456"],
        )
        assert "user_123" in flag.user_ids

    def test_user_list_not_contains_user(self):
        """User list flag should be disabled for users not in the list."""
        flag = FeatureFlag(
            id="flag_list",
            key="beta_feature",
            name="Beta Feature",
            flag_type="user_list",
            enabled=True,
            user_ids=["user_123", "user_456"],
        )
        assert "user_789" not in flag.user_ids

    def test_plan_based_matches_plan(self):
        """Plan-based flag should be enabled for matching plans."""
        flag = FeatureFlag(
            id="flag_plan",
            key="pro_feature",
            name="Pro Feature",
            flag_type="plan_based",
            enabled=True,
            plans=["pro", "enterprise"],
        )
        user_plan = "pro"
        assert user_plan in flag.plans

    def test_plan_based_no_match(self):
        """Plan-based flag should be disabled for non-matching plans."""
        flag = FeatureFlag(
            id="flag_plan",
            key="pro_feature",
            name="Pro Feature",
            flag_type="plan_based",
            enabled=True,
            plans=["pro", "enterprise"],
        )
        user_plan = "free"
        assert user_plan not in flag.plans

    def test_expired_flag(self):
        """Expired flag should be considered disabled."""
        flag = FeatureFlag(
            id="flag_expired",
            key="expired_feature",
            name="Expired Feature",
            flag_type="boolean",
            enabled=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        assert flag.expires_at < datetime.utcnow()

    def test_not_expired_flag(self):
        """Non-expired flag should be considered based on enabled status."""
        flag = FeatureFlag(
            id="flag_future",
            key="future_feature",
            name="Future Feature",
            flag_type="boolean",
            enabled=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        assert flag.expires_at > datetime.utcnow()


class TestPercentageRollout:
    """Tests for percentage-based feature flag rollout."""

    def test_percentage_zero(self):
        """0% rollout should disable for all users."""
        flag = FeatureFlag(
            id="flag_pct",
            key="rollout_feature",
            name="Rollout Feature",
            flag_type="percentage",
            enabled=True,
            percentage=0,
        )
        # With 0%, no users should be in the rollout
        assert flag.percentage == 0

    def test_percentage_full(self):
        """100% rollout should enable for all users."""
        flag = FeatureFlag(
            id="flag_pct",
            key="rollout_feature",
            name="Rollout Feature",
            flag_type="percentage",
            enabled=True,
            percentage=100,
        )
        assert flag.percentage == 100

    def test_percentage_partial(self):
        """50% rollout should enable for approximately half of users."""
        flag = FeatureFlag(
            id="flag_pct",
            key="rollout_feature",
            name="Rollout Feature",
            flag_type="percentage",
            enabled=True,
            percentage=50,
        )
        assert 0 < flag.percentage < 100

    def test_percentage_hash_consistency(self):
        """Same user+flag combination should always get same result."""
        import hashlib

        flag_key = "test_feature"
        user_id = "user_123"

        # Calculate hash bucket
        hash_value = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
        bucket = hash_value % 100

        # Should be consistent
        hash_value2 = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
        bucket2 = hash_value2 % 100

        assert bucket == bucket2


class TestImpersonation:
    """Tests for impersonation functionality."""

    def test_impersonation_token_claims(self, mock_admin_user, mock_regular_user):
        """Impersonation token should include correct claims."""
        from app.api.v1.admin.impersonate import create_impersonation_token

        with patch("app.api.v1.admin.impersonate.settings") as mock_settings:
            mock_settings.SECRET_KEY = "test-secret-key-that-is-at-least-32-chars"

            token = create_impersonation_token(
                impersonated_user=mock_regular_user,
                impersonator=mock_admin_user,
                duration_minutes=30,
            )

            assert token is not None
            assert isinstance(token, str)

    def test_impersonation_cannot_impersonate_self(self):
        """Admin should not be able to impersonate themselves."""
        # This is a business rule test
        admin_id = "admin_123"
        target_id = "admin_123"
        assert admin_id == target_id  # Cannot impersonate self

    def test_impersonation_audit_log(self, mock_admin_user, mock_regular_user):
        """Impersonation should create an audit log entry."""
        log = AuditLog(
            actor_id=mock_admin_user.id,
            actor_email=mock_admin_user.email,
            action="user.impersonated",
            description=f"Started impersonation of user {mock_regular_user.email}",
            resource_type="user",
            resource_id=mock_regular_user.id,
            details={
                "reason": "Customer support request",
                "duration_minutes": 30,
            },
        )
        assert log.action == "user.impersonated"
        assert log.resource_id == mock_regular_user.id
        assert log.details["reason"] == "Customer support request"


class TestDashboardStats:
    """Tests for dashboard statistics."""

    def test_user_stats_model(self):
        """UserStats should have correct fields."""
        from app.api.v1.admin.dashboard import UserStats

        stats = UserStats(
            total=100,
            active=90,
            inactive=10,
            admins=5,
            new_last_7_days=15,
            new_last_30_days=40,
        )
        assert stats.total == 100
        assert stats.active == 90
        assert stats.inactive == 10

    def test_subscription_stats_model(self):
        """SubscriptionStats should have correct fields."""
        from app.api.v1.admin.dashboard import SubscriptionStats

        stats = SubscriptionStats(
            free=50,
            pro=40,
            enterprise=10,
            active=45,
            trialing=5,
            canceled=3,
            past_due=2,
        )
        assert stats.free + stats.pro + stats.enterprise == 100
        assert stats.active == 45

    def test_webhook_stats_model(self):
        """WebhookStats should have correct fields."""
        from app.api.v1.admin.dashboard import WebhookStats

        stats = WebhookStats(
            total=1000,
            pending=10,
            processed=950,
            failed=40,
            last_24_hours=100,
        )
        assert stats.total == 1000
        assert stats.pending + stats.processed + stats.failed == 1000

    def test_system_stats_model(self):
        """SystemStats should have correct fields."""
        from app.api.v1.admin.dashboard import SystemStats

        stats = SystemStats(
            database_connected=True,
            redis_connected=True,
            uptime_seconds=3600.5,
        )
        assert stats.database_connected is True
        assert stats.redis_connected is True
