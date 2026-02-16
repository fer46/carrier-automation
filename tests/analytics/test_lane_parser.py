from app.analytics.lane_parser import parse_lane, resolve_city


class TestResolveCity:
    def test_canonical_form(self):
        assert resolve_city("Chicago, IL") == "Chicago, IL"

    def test_lowercase(self):
        assert resolve_city("chicago, il") == "Chicago, IL"

    def test_no_comma(self):
        assert resolve_city("chicago il") == "Chicago, IL"

    def test_city_only(self):
        assert resolve_city("Dallas") == "Dallas, TX"

    def test_whitespace_stripped(self):
        assert resolve_city("  Houston  ") == "Houston, TX"

    def test_unresolvable_returns_none(self):
        assert resolve_city("Timbuktu") is None

    def test_empty_returns_none(self):
        assert resolve_city("") is None

    def test_none_returns_none(self):
        assert resolve_city(None) is None


class TestParseLane:
    def test_unicode_arrow(self):
        result = parse_lane("Chicago, IL \u2192 Dallas, TX")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_ascii_arrow(self):
        result = parse_lane("Chicago, IL -> Dallas, TX")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_dash_separator(self):
        result = parse_lane("Chicago, IL - Dallas, TX")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_to_separator(self):
        result = parse_lane("Chicago to Dallas")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_to_separator_case_insensitive(self):
        result = parse_lane("chicago TO dallas")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_no_comma_with_state(self):
        result = parse_lane("Chicago IL -> Dallas TX")
        assert result == ("Chicago, IL", "Dallas, TX")

    def test_unresolvable_origin(self):
        assert parse_lane("Timbuktu -> Dallas, TX") is None

    def test_unresolvable_destination(self):
        assert parse_lane("Chicago, IL -> Timbuktu") is None

    def test_empty_returns_none(self):
        assert parse_lane("") is None

    def test_none_returns_none(self):
        assert parse_lane(None) is None

    def test_no_separator(self):
        assert parse_lane("Chicago IL Dallas TX") is None
