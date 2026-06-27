from example_core.geometry import manhattan


def test_manhattan_basic():
    assert manhattan((0, 0), (3, 4)) == 7


def test_manhattan_zero():
    assert manhattan((1, 1), (1, 1)) == 0
