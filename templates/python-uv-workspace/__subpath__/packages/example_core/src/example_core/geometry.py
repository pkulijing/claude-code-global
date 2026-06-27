"""纯几何工具：演示「可独立单测的纯逻辑」放库成员（不依赖任何运行时环境）。"""


def manhattan(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点的曼哈顿距离 |dx| + |dy|。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
