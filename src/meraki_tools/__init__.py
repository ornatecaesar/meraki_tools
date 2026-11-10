"""Command-line tools for automating and reporting on Cisco Meraki networks.

The package is split by area:

* :mod:`meraki_tools.core` - shared building blocks (API client, logging,
  organisation lookup, VLAN list helpers and action batches).
* :mod:`meraki_tools.switching` - switch port configuration and audits.
* :mod:`meraki_tools.wireless` - wireless and access point trunk tools.
* :mod:`meraki_tools.reporting` - utilisation reports and snapshots.
* :mod:`meraki_tools.backups` - configuration backups.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("meraki-tools")
except PackageNotFoundError:  # Running from a source checkout that is not installed.
    __version__ = "0.0.0"

__all__ = ["__version__"]
