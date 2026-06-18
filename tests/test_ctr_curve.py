from seo_gsc.ctr_curve import expected_ctr, DEFAULT_CTR_CURVE


def test_position_one_is_highest():
    assert expected_ctr(1.0) == DEFAULT_CTR_CURVE[1]
    assert expected_ctr(1.0) > expected_ctr(5.0) > expected_ctr(10.0)


def test_interpolates_fractional_position():
    val = expected_ctr(2.5)
    assert DEFAULT_CTR_CURVE[3] < val < DEFAULT_CTR_CURVE[2]


def test_clamps_below_one():
    assert expected_ctr(0.4) == DEFAULT_CTR_CURVE[1]


def test_tail_beyond_table_is_small_and_flat():
    assert expected_ctr(35.0) <= 0.006
    assert expected_ctr(50.0) == expected_ctr(40.0)


def test_custom_curve_override():
    curve = {1: 0.5, 2: 0.25}
    assert expected_ctr(1.0, curve) == 0.5
    assert abs(expected_ctr(1.5, curve) - 0.375) < 1e-9
