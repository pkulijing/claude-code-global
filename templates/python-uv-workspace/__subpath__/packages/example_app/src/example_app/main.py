"""应用成员入口：演示跨成员 import（依赖 example_core，经 workspace source 解析到本仓源码）。"""

from example_core.geometry import manhattan


def total_path(points: list[tuple[float, float]]) -> float:
    """相邻点曼哈顿距离之和（折线总长）。"""
    return sum(manhattan(points[i], points[i + 1]) for i in range(len(points) - 1))


def main() -> None:
    print(total_path([(0, 0), (1, 1), (4, 5)]))
