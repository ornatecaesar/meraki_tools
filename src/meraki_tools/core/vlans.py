"""Read and edit the ``allowedVlans`` string on Meraki trunk ports.

The Dashboard API represents a trunk's allowed VLANs as a string such as
``"1,16,100-110"`` or ``"all"``. These helpers turn that string into a set of
VLAN IDs, change it, and write it back in the compact form the Dashboard uses.
"""

from __future__ import annotations

ALL_VLANS = "all"

#: Valid 802.1Q VLAN IDs.
MIN_VLAN = 1
MAX_VLAN = 4094


def parse_vlan_list(allowed_vlans: str) -> set[int] | None:
    """Expand an ``allowedVlans`` string into a set of VLAN IDs.

    Args:
        allowed_vlans: A string such as ``"1,16,100-110"`` or ``"all"``.
            Whitespace around items is ignored.

    Returns:
        The set of VLAN IDs, or ``None`` if the string allows all VLANs.

    Raises:
        ValueError: If an item is not a number or a ``start-end`` range, or a
            range runs backwards.

    Example:
        >>> sorted(parse_vlan_list("1, 5-7"))
        [1, 5, 6, 7]
    """
    if ALL_VLANS in allowed_vlans.lower():
        return None

    vlans: set[int] = set()
    for raw_item in allowed_vlans.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", maxsplit=1)
            start, end = int(start_text), int(end_text)
            if start > end:
                raise ValueError(f"VLAN range runs backwards: {item!r}")
            vlans.update(range(start, end + 1))
        else:
            vlans.add(int(item))
    return vlans


def format_vlan_list(vlans: set[int]) -> str:
    """Write a set of VLAN IDs as a compact ``allowedVlans`` string.

    Runs of three or more consecutive IDs become ranges, so the output matches
    what the Dashboard shows.

    Args:
        vlans: VLAN IDs to include.

    Returns:
        A string such as ``"1,16,100-110"``.

    Example:
        >>> format_vlan_list({1, 2, 3, 7, 9, 10})
        '1-3,7,9,10'
    """
    parts: list[str] = []
    ordered = sorted(vlans)
    i = 0
    while i < len(ordered):
        start = ordered[i]
        while i + 1 < len(ordered) and ordered[i + 1] == ordered[i] + 1:
            i += 1
        end = ordered[i]
        if end - start >= 2:
            parts.append(f"{start}-{end}")
        else:
            parts.extend(str(v) for v in range(start, end + 1))
        i += 1
    return ",".join(parts)


def is_vlan_in_list(vlan: int, allowed_vlans: str) -> bool:
    """Return whether a VLAN is carried by a trunk with this ``allowedVlans`` value.

    Unlike the copies in the original scripts, ``"all"`` counts as a match,
    because a trunk that allows all VLANs does carry the VLAN.

    Args:
        vlan: The VLAN ID to look for.
        allowed_vlans: The port's ``allowedVlans`` string.

    Returns:
        ``True`` if the VLAN is allowed on the trunk.
    """
    vlans = parse_vlan_list(allowed_vlans)
    return vlans is None or vlan in vlans


def add_vlan_to_list(vlan: int, allowed_vlans: str) -> str:
    """Return ``allowedVlans`` with a VLAN added.

    Args:
        vlan: The VLAN ID to add.
        allowed_vlans: The port's current ``allowedVlans`` string.

    Returns:
        The updated string. It is returned unchanged if the VLAN is already
        allowed, including when the trunk allows all VLANs.
    """
    _check_vlan_id(vlan)
    vlans = parse_vlan_list(allowed_vlans)
    if vlans is None or vlan in vlans:
        return allowed_vlans
    return format_vlan_list(vlans | {vlan})


def remove_vlan_from_list(vlan: int, allowed_vlans: str) -> str:
    """Return ``allowedVlans`` with a VLAN removed, splitting ranges if needed.

    Args:
        vlan: The VLAN ID to remove.
        allowed_vlans: The port's current ``allowedVlans`` string.

    Returns:
        The updated string. It is returned unchanged when the VLAN is not in
        the list, when the trunk allows all VLANs (there is no way to express
        "all except one" without listing every other VLAN), or when removing
        it would leave the list empty, which the Dashboard rejects.

    Example:
        >>> remove_vlan_from_list(45, "16,40-50")
        '16,40-44,46-50'
    """
    _check_vlan_id(vlan)
    vlans = parse_vlan_list(allowed_vlans)
    if vlans is None or vlan not in vlans or vlans == {vlan}:
        return allowed_vlans
    return format_vlan_list(vlans - {vlan})


def _check_vlan_id(vlan: int) -> None:
    if not MIN_VLAN <= vlan <= MAX_VLAN:
        raise ValueError(f"VLAN ID must be between {MIN_VLAN} and {MAX_VLAN}, got {vlan}")
