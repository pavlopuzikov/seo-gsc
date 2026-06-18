from seo_gsc.analysis import compare_periods, build_weekly_markdown, split_by_date


def test_compare_periods_returns_site_and_movers(current_period, previous_period):
    result = compare_periods(current_period, previous_period)
    assert result["site"].entity == "site"
    assert result["dimension"] in {"page", "query"}
    assert isinstance(result["gainers"], list)
    assert isinstance(result["losers"], list)


def test_site_delta_clicks_change(current_period, previous_period):
    site = compare_periods(current_period, previous_period)["site"]
    assert site.clicks == current_period.totals()["clicks"]
    assert site.clicks_prev == previous_period.totals()["clicks"]


def test_split_by_date(dataset):
    previous, current = split_by_date(dataset, "2026-06-08")
    assert (previous.df["date"] < "2026-06-08").all()
    assert (current.df["date"] >= "2026-06-08").all()


def test_weekly_markdown_has_sections(current_period, previous_period):
    md = build_weekly_markdown(current_period, previous_period, property_name="test.com")
    assert "SEO weekly report" in md
    assert "Site movement" in md
    assert "Priorities for next week" in md
    # House rule: no em or en dashes in generated output.
    assert "—" not in md and "–" not in md
