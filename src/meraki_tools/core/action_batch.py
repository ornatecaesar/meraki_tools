"""Queue configuration changes and send them to Meraki as action batches.

Action batches apply many changes in one API call, which is much faster and
gentler on the rate limit than one call per port. Meraki caps a synchronous
batch at 20 actions and an asynchronous one at 100, so :class:`ActionBatcher`
sends a batch each time the queue fills and once more at the end.

Typical use::

    with ActionBatcher(dashboard, org_id, dry_run=args.dry_run) as batcher:
        for port in ports:
            batcher.update(f"/devices/{serial}/switch/ports/{port['portId']}", {"stpGuard": "bpdu guard"})
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any, Self

import meraki

from meraki_tools.core.errors import format_api_error

logger = logging.getLogger(__name__)

#: Maximum actions Meraki accepts in one synchronous action batch.
SYNC_BATCH_LIMIT = 20
#: Maximum actions Meraki accepts in one asynchronous action batch.
ASYNC_BATCH_LIMIT = 100


class ActionBatcher:
    """Collect actions and submit them in batches of the allowed size.

    Attributes:
        submitted: Number of actions sent successfully (or logged, in dry-run mode).
        failed: Number of actions in batches that the API rejected.
        responses: The API response for each batch that was sent.
    """

    def __init__(
        self,
        dashboard: meraki.DashboardAPI,
        organization_id: str,
        *,
        synchronous: bool = True,
        dry_run: bool = False,
    ) -> None:
        """Create a batcher for one organisation.

        Args:
            dashboard: Dashboard API client.
            organization_id: Organisation that owns the resources being changed.
            synchronous: Wait for each batch to finish before returning, so
                errors are reported straight away. Synchronous batches hold
                up to 20 actions; asynchronous ones up to 100.
            dry_run: Log each action instead of sending it.
        """
        self._dashboard = dashboard
        self._organization_id = organization_id
        self._synchronous = synchronous
        self._dry_run = dry_run
        self._limit = SYNC_BATCH_LIMIT if synchronous else ASYNC_BATCH_LIMIT
        self._pending: list[dict[str, Any]] = []
        self.submitted = 0
        self.failed = 0
        self.responses: list[dict[str, Any]] = []

    def add(self, resource: str, operation: str, body: dict[str, Any]) -> None:
        """Queue one action, sending a batch if the queue is now full.

        Args:
            resource: API path of the object to change, for example
                ``"/devices/Q2XX-XXXX-XXXX/switch/ports/12"``.
            operation: Action batch operation, such as ``"update"`` or ``"create"``.
            body: The fields to send, as for the matching single API call.
        """
        self._pending.append({"resource": resource, "operation": operation, "body": body})
        if len(self._pending) >= self._limit:
            self.flush()

    def update(self, resource: str, body: dict[str, Any]) -> None:
        """Queue an ``update`` action. Shorthand for ``add(resource, "update", body)``."""
        self.add(resource, "update", body)

    def flush(self) -> None:
        """Send any queued actions now."""
        if not self._pending:
            return

        actions, self._pending = self._pending, []

        if self._dry_run:
            for action in actions:
                logger.debug("[dry run] %s %s %s", action["operation"], action["resource"], action["body"])
            self.submitted += len(actions)
            return

        try:
            response = self._dashboard.organizations.createOrganizationActionBatch(
                organizationId=self._organization_id,
                actions=actions,
                confirmed=True,
                synchronous=self._synchronous,
            )
        except meraki.APIError as error:
            self.failed += len(actions)
            logger.error("Action batch of %d actions failed: %s", len(actions), format_api_error(error))
            return

        self.responses.append(response)
        status = response.get("status", {})
        if status.get("failed"):
            self.failed += len(actions)
            logger.error("Action batch %s failed: %s", response.get("id"), status.get("errors"))
        else:
            self.submitted += len(actions)
            logger.info("Action batch %s accepted with %d actions", response.get("id"), len(actions))

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Send what is queued only when the block finished normally, so a crash
        # part-way through does not push a half-built set of changes.
        if exc_type is None:
            self.flush()
        elif self._pending:
            logger.warning("Discarded %d queued actions because of an error", len(self._pending))
            self._pending.clear()
