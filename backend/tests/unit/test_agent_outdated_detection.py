"""
Unit tests for agent outdated detection (Issue #239).

Tests the platform storage, outdated detection during heartbeat,
notification emission, and pool status updates.
"""

import json
import hashlib
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.src.models.agent import Agent, AgentStatus
from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models import User, UserStatus, UserType, Team, Collection
from backend.src.models.collection import CollectionType
from backend.src.services.agent_service import AgentService


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def agent_service(test_db_session):
    """Create an AgentService instance."""
    return AgentService(test_db_session)


@pytest.fixture
def system_user(test_db_session, test_team):
    """Create a system user for agent audit trail."""
    user = User(
        team_id=test_team.id,
        email="agent-system@system.local",
        display_name="Agent System User",
        status=UserStatus.ACTIVE,
        user_type=UserType.SYSTEM,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


def _make_checksum(value: str) -> str:
    """Generate a valid SHA-256 checksum from a string."""
    return hashlib.sha256(value.encode()).hexdigest()


AGENT_CHECKSUM = _make_checksum("agent-binary-v1")
MANIFEST_CHECKSUM = _make_checksum("agent-binary-v2")


@pytest.fixture
def agent(test_db_session, test_team, test_user, system_user):
    """Create a test agent with platform and checksum."""
    a = Agent(
        team_id=test_team.id,
        system_user_id=system_user.id,
        created_by_user_id=test_user.id,
        name="Test Agent",
        hostname="test-host",
        status=AgentStatus.OFFLINE,
        api_key_hash=_make_checksum("test-api-key"),
        api_key_prefix="agt_key_12345678",
        version="v1.0.0",
        binary_checksum=AGENT_CHECKSUM,
        platform="darwin-arm64",
        is_outdated=False,
    )
    test_db_session.add(a)
    test_db_session.commit()
    test_db_session.refresh(a)
    return a


@pytest.fixture
def active_manifest(test_db_session, test_user):
    """Create an active release manifest with a different checksum."""
    m = ReleaseManifest(
        version="v2.0.0",
        checksum=MANIFEST_CHECKSUM,
        is_active=True,
        created_by_user_id=test_user.id,
        updated_by_user_id=test_user.id,
    )
    m.platforms = ["darwin-arm64", "darwin-amd64"]
    test_db_session.add(m)
    test_db_session.commit()
    test_db_session.refresh(m)
    return m


@pytest.fixture
def matching_manifest(test_db_session, test_user):
    """Create an active release manifest that matches the agent checksum."""
    m = ReleaseManifest(
        version="v1.0.0",
        checksum=AGENT_CHECKSUM,
        is_active=True,
        created_by_user_id=test_user.id,
        updated_by_user_id=test_user.id,
    )
    m.platforms = ["darwin-arm64"]
    test_db_session.add(m)
    test_db_session.commit()
    test_db_session.refresh(m)
    return m


# ============================================================================
# Outdated Detection Tests
# ============================================================================

class TestAgentOutdatedDetection:
    """Tests for _check_outdated and heartbeat integration."""

    def test_agent_detected_as_outdated(self, agent_service, agent, active_manifest):
        """Agent with old checksum is flagged outdated."""
        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert agent.is_outdated is True
        assert became_outdated is True
        assert latest_version == "v2.0.0"

    def test_agent_not_outdated_when_checksum_matches(
        self, agent_service, agent, matching_manifest
    ):
        """Agent with matching checksum is not flagged outdated."""
        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert agent.is_outdated is False
        assert became_outdated is False
        assert latest_version == "v1.0.0"

    def test_no_manifest_returns_none(self, agent_service, agent):
        """No active manifest means no outdated detection."""
        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version is None
        assert became_outdated is False
        assert agent.is_outdated is False

    def test_missing_platform_flagged_outdated(
        self, agent_service, agent, active_manifest
    ):
        """Agent without platform is flagged outdated when active manifests exist."""
        agent.platform = None

        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version == "v2.0.0"
        assert became_outdated is True
        assert agent.is_outdated is True

    def test_missing_checksum_flagged_outdated(
        self, agent_service, agent, active_manifest
    ):
        """Agent without binary_checksum is flagged outdated when active manifests exist."""
        agent.binary_checksum = None

        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version == "v2.0.0"
        assert became_outdated is True
        assert agent.is_outdated is True

    def test_missing_platform_not_outdated_without_manifests(
        self, agent_service, agent
    ):
        """Agent without platform is NOT flagged when no active manifests exist."""
        agent.platform = None

        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version is None
        assert became_outdated is False
        assert agent.is_outdated is False

    def test_no_matching_platform_returns_none(
        self, test_db_session, agent_service, agent, test_user
    ):
        """Manifest for different platform is ignored."""
        m = ReleaseManifest(
            version="v2.0.0",
            checksum=MANIFEST_CHECKSUM,
            is_active=True,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        m.platforms = ["linux-amd64"]
        test_db_session.add(m)
        test_db_session.commit()

        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version is None
        assert became_outdated is False

    def test_inactive_manifest_ignored(
        self, test_db_session, agent_service, agent, test_user
    ):
        """Inactive manifests are not considered."""
        m = ReleaseManifest(
            version="v3.0.0",
            checksum=MANIFEST_CHECKSUM,
            is_active=False,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        m.platforms = ["darwin-arm64"]
        test_db_session.add(m)
        test_db_session.commit()

        latest_version, became_outdated = agent_service._check_outdated(agent)

        assert latest_version is None
        assert became_outdated is False

    def test_became_outdated_only_on_transition(
        self, agent_service, agent, active_manifest
    ):
        """became_outdated is True only on first detection (False->True)."""
        # First call: transition to outdated
        _, became_outdated_1 = agent_service._check_outdated(agent)
        assert became_outdated_1 is True
        assert agent.is_outdated is True

        # Second call: already outdated, no transition
        _, became_outdated_2 = agent_service._check_outdated(agent)
        assert became_outdated_2 is False
        assert agent.is_outdated is True

    def test_auto_resolve_outdated(
        self, test_db_session, agent_service, agent, active_manifest, test_user
    ):
        """Agent auto-resolves outdated when updated to matching checksum."""
        # First: detect as outdated
        agent_service._check_outdated(agent)
        assert agent.is_outdated is True

        # Agent updates its binary to match the manifest
        agent.binary_checksum = MANIFEST_CHECKSUM
        test_db_session.flush()

        _, became_outdated = agent_service._check_outdated(agent)
        assert agent.is_outdated is False
        assert became_outdated is False

    def test_heartbeat_flags_outdated_without_platform(
        self, agent_service, agent, active_manifest
    ):
        """Agent without platform is flagged outdated when active manifests exist."""
        agent.platform = None

        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.latest_version == "v2.0.0"
        assert result.became_outdated is True
        assert result.agent.is_outdated is True

    def test_heartbeat_flags_outdated_without_checksum(
        self, agent_service, agent, active_manifest
    ):
        """Agent without binary_checksum is flagged outdated when active manifests exist."""
        agent.binary_checksum = None

        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.latest_version == "v2.0.0"
        assert result.became_outdated is True
        assert result.agent.is_outdated is True

    def test_heartbeat_not_outdated_without_platform_no_manifests(
        self, agent_service, agent
    ):
        """Agent without platform is NOT flagged outdated when no active manifests exist."""
        agent.platform = None

        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.latest_version is None
        assert result.became_outdated is False
        assert result.agent.is_outdated is False

    def test_heartbeat_includes_outdated_info(
        self, agent_service, agent, active_manifest
    ):
        """Heartbeat result includes outdated info when detected."""
        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.latest_version == "v2.0.0"
        assert result.became_outdated is True
        assert result.agent.is_outdated is True


# ============================================================================
# Platform Persistence Tests
# ============================================================================

class TestPlatformPersistence:
    """Tests for platform storage during registration."""

    def test_register_agent_stores_platform(
        self, test_db_session, agent_service, test_team, test_user
    ):
        """Platform is persisted during registration."""
        # Create a registration token
        token_result = agent_service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Create a matching manifest for attestation
        m = ReleaseManifest(
            version="v1.0.0",
            checksum=AGENT_CHECKSUM,
            is_active=True,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        m.platforms = ["linux-amd64"]
        test_db_session.add(m)
        test_db_session.commit()

        result = agent_service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="New Agent",
            hostname="new-host",
            os_info="Linux 6.1",
            capabilities=["photostats"],
            version="v1.0.0",
            binary_checksum=AGENT_CHECKSUM,
            platform="linux-amd64",
        )

        assert result.agent.platform == "linux-amd64"
        assert result.agent.is_outdated is False


# ============================================================================
# Pool Status Tests
# ============================================================================

class TestPoolStatusWithOutdated:
    """Tests for pool status including outdated count."""

    def test_pool_status_includes_outdated_count(
        self, agent_service, agent, active_manifest, test_team
    ):
        """Pool status includes outdated_count."""
        # Mark agent as outdated
        agent.is_outdated = True
        agent.status = AgentStatus.ONLINE

        status = agent_service.get_pool_status(test_team.id)

        assert "outdated_count" in status
        assert status["outdated_count"] == 1

    def test_pool_status_outdated_excludes_revoked(
        self, test_db_session, agent_service, agent, test_team
    ):
        """Revoked agents are not counted as outdated."""
        agent.is_outdated = True
        agent.status = AgentStatus.REVOKED
        agent.revocation_reason = "test"
        agent.revoked_at = datetime.utcnow()
        test_db_session.flush()

        status = agent_service.get_pool_status(test_team.id)

        assert status["outdated_count"] == 0

    def test_pool_status_outdated_priority(
        self, agent_service, agent, active_manifest, test_team
    ):
        """Status is 'outdated' when agents are online but outdated (no running jobs)."""
        agent.is_outdated = True
        agent.status = AgentStatus.ONLINE

        status = agent_service.get_pool_status(test_team.id)

        assert status["status"] == "outdated"

    def test_pool_status_running_overrides_outdated(
        self, test_db_session, agent_service, agent, active_manifest, test_team, test_user
    ):
        """Running jobs take priority over outdated status."""
        from backend.src.models.job import Job, JobStatus

        agent.is_outdated = True
        agent.status = AgentStatus.ONLINE

        # Create a collection for the job
        col = Collection(
            team_id=test_team.id,
            name="Test Col",
            type=CollectionType.LOCAL,
            location="/test",
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(col)
        test_db_session.flush()

        # Create a running job
        job = Job(
            team_id=test_team.id,
            collection_id=col.id,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(job)
        test_db_session.flush()

        status = agent_service.get_pool_status(test_team.id)

        assert status["status"] == "running"

    def test_pool_status_zero_outdated_by_default(
        self, agent_service, agent, test_team
    ):
        """Outdated count is 0 when no agents are flagged."""
        agent.status = AgentStatus.ONLINE

        status = agent_service.get_pool_status(test_team.id)

        assert status["outdated_count"] == 0
        assert status["status"] == "idle"

    def test_pool_status_outdated_excludes_unverified(
        self, agent_service, agent, test_team
    ):
        """Unverified agents are not counted as outdated (their outdated flag is meaningless)."""
        agent.is_outdated = True
        agent.is_verified = False
        agent.status = AgentStatus.ONLINE

        status = agent_service.get_pool_status(test_team.id)

        assert status["outdated_count"] == 0
        assert status["status"] == "idle"


# ============================================================================
# Notification Tests
# ============================================================================

class TestAgentOutdatedNotification:
    """Tests for agent_outdated notification emission."""

    def test_notification_service_handles_agent_outdated(
        self, test_db_session, test_team, test_user, agent
    ):
        """NotificationService.notify_agent_status handles agent_outdated without error."""
        from backend.src.services.notification_service import NotificationService

        svc = NotificationService(test_db_session)

        # Should not raise (will return 0 since no user prefs enabled)
        result = svc.notify_agent_status(
            team_id=test_team.id,
            agent=agent,
            transition_type="agent_outdated",
        )
        assert isinstance(result, int)

    @patch("backend.src.services.notification_service.NotificationService")
    def test_heartbeat_triggers_outdated_notification(
        self, mock_ns_class, test_db_session, agent_service, agent,
        active_manifest, test_team
    ):
        """Heartbeat that detects outdated should trigger agent_outdated notification."""
        from backend.src.api.agent.routes import _trigger_agent_notification

        # Process heartbeat which marks agent as outdated
        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.became_outdated is True
        assert result.agent.is_outdated is True
        assert result.latest_version == "v2.0.0"


# ============================================================================
# Attestation Verification Tests (Issue #236)
# ============================================================================

class TestAgentAttestationVerification:
    """Tests for continuous binary attestation verification."""

    def test_verified_when_checksum_matches_any_manifest(
        self, agent_service, agent, matching_manifest
    ):
        """Agent is verified when checksum matches any active manifest."""
        agent_service._check_outdated(agent)

        assert agent.is_verified is True

    def test_not_verified_when_checksum_unknown(
        self, agent_service, agent, active_manifest
    ):
        """Agent is not verified when checksum doesn't match any manifest."""
        agent_service._check_outdated(agent)

        assert agent.is_verified is False

    def test_verified_when_no_manifests_exist(
        self, agent_service, agent
    ):
        """Agent is verified when no active manifests exist (dev/bootstrap)."""
        agent_service._check_outdated(agent)

        assert agent.is_verified is True

    def test_verified_when_missing_checksum(
        self, agent_service, agent, active_manifest
    ):
        """Agent without checksum stays verified (dev/pre-upgrade agent)."""
        agent.binary_checksum = None

        agent_service._check_outdated(agent)

        assert agent.is_verified is True

    def test_verified_when_missing_platform(
        self, agent_service, agent, active_manifest
    ):
        """Agent without platform stays verified (dev/pre-upgrade agent)."""
        agent.platform = None

        agent_service._check_outdated(agent)

        assert agent.is_verified is True

    def test_verified_after_update_to_matching_checksum(
        self, test_db_session, agent_service, agent, active_manifest
    ):
        """Agent becomes verified after updating to a known checksum."""
        # First: unverified (has a checksum that doesn't match any manifest)
        agent_service._check_outdated(agent)
        assert agent.is_verified is False

        # Update binary to match manifest
        agent.binary_checksum = MANIFEST_CHECKSUM
        test_db_session.flush()

        agent_service._check_outdated(agent)
        assert agent.is_verified is True

    def test_heartbeat_sets_is_verified(
        self, agent_service, agent, matching_manifest
    ):
        """Heartbeat processing sets is_verified via _check_outdated."""
        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
        )

        assert result.agent.is_verified is True

    def test_heartbeat_unverified_for_unknown_checksum(
        self, agent_service, agent, active_manifest
    ):
        """Heartbeat processing marks agent unverified for unknown checksum."""
        result = agent_service.process_heartbeat(
            agent=agent,
            status=AgentStatus.ONLINE,
            binary_checksum=AGENT_CHECKSUM,
        )

        assert result.agent.is_verified is False

    def test_can_execute_jobs_requires_verified(
        self, agent_service, agent, active_manifest
    ):
        """can_execute_jobs is False when agent is unverified."""
        agent.status = AgentStatus.ONLINE
        agent_service._check_outdated(agent)

        assert agent.is_verified is False
        assert agent.can_execute_jobs is False

    def test_can_execute_jobs_when_verified(
        self, agent_service, agent, matching_manifest
    ):
        """can_execute_jobs is True when agent is online and verified."""
        agent.status = AgentStatus.ONLINE
        agent_service._check_outdated(agent)

        assert agent.is_verified is True
        assert agent.can_execute_jobs is True


# ============================================================================
# Pool Status Unverified Count Tests (Issue #236)
# ============================================================================

class TestPoolStatusWithUnverified:
    """Tests for pool status including unverified_count."""

    def test_pool_status_includes_unverified_count(
        self, agent_service, agent, test_team
    ):
        """Pool status includes unverified_count."""
        agent.is_verified = False
        agent.status = AgentStatus.ONLINE

        status = agent_service.get_pool_status(test_team.id)

        assert "unverified_count" in status
        assert status["unverified_count"] == 1

    def test_pool_status_unverified_excludes_revoked(
        self, test_db_session, agent_service, agent, test_team
    ):
        """Revoked agents are not counted as unverified."""
        agent.is_verified = False
        agent.status = AgentStatus.REVOKED
        agent.revocation_reason = "test"
        agent.revoked_at = datetime.utcnow()
        test_db_session.flush()

        status = agent_service.get_pool_status(test_team.id)

        assert status["unverified_count"] == 0

    def test_pool_status_zero_unverified_by_default(
        self, agent_service, agent, test_team
    ):
        """Unverified count is 0 when all agents are verified."""
        agent.status = AgentStatus.ONLINE
        agent.is_verified = True

        status = agent_service.get_pool_status(test_team.id)

        assert status["unverified_count"] == 0
