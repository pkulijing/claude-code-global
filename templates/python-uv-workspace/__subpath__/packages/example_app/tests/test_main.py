from example_app.main import total_path


def test_total_path():
    # (0,0)->(1,1): 2 ; (1,1)->(4,5): 7 ; 合计 9
    assert total_path([(0, 0), (1, 1), (4, 5)]) == 9


def test_total_path_single_point():
    assert total_path([(2, 2)]) == 0
