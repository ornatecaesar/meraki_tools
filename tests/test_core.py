import logging
from unittest.mock import MagicMock

import pytest

from meraki_tools.core import (
    MissingAPIKeyError,
    OrganizationSelectionError,
    get_dashboard,
    get_organization_id,
    setup_logging,
)


class TestGetDashboard:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("MERAKI_API_KEY", raising=False)
        with pytest.raises(MissingAPIKeyError):
            get_dashboard()

    def test_reads_key_from_environment(self, monkeypatch):
        monkeypatch.setenv("MERAKI_API_KEY", "a" * 40)
        dashboard = get_dashboard()
        assert dashboard.organizations is not None


class TestGetOrganizationId:
    def test_explicit_id_wins(self, monkeypatch):
        monkeypatch.setenv("MERAKI_ORG_ID", "from-env")
        assert get_organization_id(MagicMock(), "explicit") == "explicit"

    def test_environment_variable(self, monkeypatch):
        monkeypatch.setenv("MERAKI_ORG_ID", "from-env")
        dashboard = MagicMock()
        assert get_organization_id(dashboard) == "from-env"
        dashboard.organizations.getOrganizations.assert_not_called()

    def test_single_org_is_used(self, monkeypatch):
        monkeypatch.delenv("MERAKI_ORG_ID", raising=False)
        dashboard = MagicMock()
        dashboard.organizations.getOrganizations.return_value = [{"id": "1", "name": "Only"}]
        assert get_organization_id(dashboard) == "1"

    def test_several_orgs_raise(self, monkeypatch):
        monkeypatch.delenv("MERAKI_ORG_ID", raising=False)
        dashboard = MagicMock()
        dashboard.organizations.getOrganizations.return_value = [
            {"id": "1", "name": "A"},
            {"id": "2", "name": "B"},
        ]
        with pytest.raises(OrganizationSelectionError, match="A \\(1\\), B \\(2\\)"):
            get_organization_id(dashboard)

    def test_no_orgs_raise(self, monkeypatch):
        monkeypatch.delenv("MERAKI_ORG_ID", raising=False)
        dashboard = MagicMock()
        dashboard.organizations.getOrganizations.return_value = []
        with pytest.raises(OrganizationSelectionError):
            get_organization_id(dashboard)


def test_setup_logging_writes_file_and_does_not_duplicate(tmp_path):
    setup_logging("demo", log_dir=tmp_path)
    logger = setup_logging("demo", log_dir=tmp_path)
    logger.info("hello")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert (tmp_path / "demo.log").read_text().count("hello") == 1
