import pytest

from meraki_tools.core.vlans import (
    add_vlan_to_list,
    format_vlan_list,
    is_vlan_in_list,
    parse_vlan_list,
    remove_vlan_from_list,
)


class TestParseVlanList:
    def test_singles_and_ranges(self):
        assert parse_vlan_list("1,16,100-103") == {1, 16, 100, 101, 102, 103}

    def test_ignores_whitespace_and_empty_items(self):
        assert parse_vlan_list(" 1 , 2,,") == {1, 2}

    @pytest.mark.parametrize("value", ["all", "ALL", "All"])
    def test_all_returns_none(self, value):
        assert parse_vlan_list(value) is None

    def test_backwards_range_is_rejected(self):
        with pytest.raises(ValueError):
            parse_vlan_list("10-5")

    def test_garbage_is_rejected(self):
        with pytest.raises(ValueError):
            parse_vlan_list("16,abc")


class TestFormatVlanList:
    def test_compresses_runs_of_three_or_more(self):
        assert format_vlan_list({1, 2, 3, 4, 10}) == "1-4,10"

    def test_keeps_pairs_as_singles(self):
        assert format_vlan_list({700, 701}) == "700,701"

    def test_empty(self):
        assert format_vlan_list(set()) == ""

    def test_round_trip(self):
        text = "1,16,150,700-705,790"
        assert format_vlan_list(parse_vlan_list(text)) == text


class TestIsVlanInList:
    def test_single_match(self):
        assert is_vlan_in_list(16, "1,16,20")

    def test_inside_range(self):
        assert is_vlan_in_list(105, "100-110")

    def test_not_present(self):
        assert not is_vlan_in_list(17, "1,16,20-30")

    def test_all_matches_everything(self):
        assert is_vlan_in_list(999, "all")


class TestAddVlanToList:
    def test_adds_and_sorts(self):
        assert add_vlan_to_list(790, "16,150,700,701") == "16,150,700,701,790"

    def test_joins_adjacent_range(self):
        assert add_vlan_to_list(4, "1-3") == "1-4"

    def test_already_present_is_unchanged(self):
        assert add_vlan_to_list(16, "1,16") == "1,16"

    def test_all_is_unchanged(self):
        assert add_vlan_to_list(16, "all") == "all"

    def test_invalid_vlan_id(self):
        with pytest.raises(ValueError):
            add_vlan_to_list(5000, "1")


class TestRemoveVlanFromList:
    def test_removes_single(self):
        assert remove_vlan_from_list(45, "16,45,100") == "16,100"

    def test_splits_range(self):
        assert remove_vlan_from_list(45, "40-50") == "40-44,46-50"

    def test_split_leaving_short_sides(self):
        assert remove_vlan_from_list(45, "44-46") == "44,46"

    def test_range_edge(self):
        assert remove_vlan_from_list(40, "40-43") == "41-43"

    def test_not_present_is_unchanged(self):
        assert remove_vlan_from_list(45, "16,100") == "16,100"

    def test_all_is_unchanged(self):
        assert remove_vlan_from_list(45, "all") == "all"

    def test_would_leave_empty_is_unchanged(self):
        assert remove_vlan_from_list(45, "45") == "45"
