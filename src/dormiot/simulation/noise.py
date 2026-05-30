from __future__ import annotations

import random


def gaussian_noise(mean: float = 0.0, std: float = 1.0) -> float:
    """生成单个高斯随机噪声值"""
    return random.gauss(mean, std)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在指定范围内"""
    return max(min_val, min(value, max_val))


def noisy_value(baseline: float, std: float, min_val: float = 0.0, max_val: float = float("inf")) -> float:
    """在基准值上叠加高斯噪声，并限制在合理范围内"""
    return clamp(baseline + gaussian_noise(0, std), min_val, max_val)
