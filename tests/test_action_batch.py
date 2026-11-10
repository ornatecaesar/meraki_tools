from unittest.mock import MagicMock

import meraki
import pytest

from meraki_tools.core.action_batch import ASYNC_BATCH_LIMIT, SYNC_BATCH_LIMIT, ActionBatcher


@pytest.fixture
def dashboard():
    mock = MagicMock()
    mock.organizations.createOrganizationActionBatch.return_value = {
        "id": "123",
        "status": {"failed": False, "errors": []},
    }
    return mock


def _send_count(dashboard):
    return dashboard.organizations.createOrganizationActionBatch.call_count


def _batch_sizes(dashboard):
    return [
        len(call.kwargs["actions"])
        for call in dashboard.organizations.createOrganizationActionBatch.call_args_list
    ]


def test_sends_full_batches_then_remainder(dashboard):
    with ActionBatcher(dashboard, "org1") as batcher:
        for port in range(SYNC_BATCH_LIMIT * 2 + 5):
            batcher.update(f"/devices/Q/switch/ports/{port}", {"enabled": True})

    assert _batch_sizes(dashboard) == [SYNC_BATCH_LIMIT, SYNC_BATCH_LIMIT, 5]
    assert batcher.submitted == SYNC_BATCH_LIMIT * 2 + 5
    assert batcher.failed == 0


def test_async_uses_larger_batches(dashboard):
    with ActionBatcher(dashboard, "org1", synchronous=False) as batcher:
        for port in range(ASYNC_BATCH_LIMIT + 1):
            batcher.update(f"/devices/Q/switch/ports/{port}", {})

    assert _batch_sizes(dashboard) == [ASYNC_BATCH_LIMIT, 1]
    assert dashboard.organizations.createOrganizationActionBatch.call_args.kwargs["synchronous"] is False


def test_dry_run_sends_nothing(dashboard):
    with ActionBatcher(dashboard, "org1", dry_run=True) as batcher:
        batcher.update("/devices/Q/switch/ports/1", {"enabled": False})

    assert _send_count(dashboard) == 0
    assert batcher.submitted == 1


def test_api_error_is_counted_not_raised(dashboard):
    response = MagicMock(status_code=400, reason="Bad Request")
    response.json.return_value = {"errors": ["nope"]}
    error = meraki.APIError(
        {"tags": ["organizations"], "operation": "createOrganizationActionBatch"}, response
    )
    dashboard.organizations.createOrganizationActionBatch.side_effect = error

    with ActionBatcher(dashboard, "org1") as batcher:
        batcher.update("/devices/Q/switch/ports/1", {})

    assert batcher.failed == 1
    assert batcher.submitted == 0


def test_failed_batch_status_is_counted(dashboard):
    dashboard.organizations.createOrganizationActionBatch.return_value = {
        "id": "9",
        "status": {"failed": True, "errors": ["port 1 invalid"]},
    }
    with ActionBatcher(dashboard, "org1") as batcher:
        batcher.update("/devices/Q/switch/ports/1", {})

    assert batcher.failed == 1


def test_exception_in_block_discards_queue(dashboard):
    with pytest.raises(RuntimeError), ActionBatcher(dashboard, "org1") as batcher:
        batcher.update("/devices/Q/switch/ports/1", {})
        raise RuntimeError("boom")

    assert _send_count(dashboard) == 0
