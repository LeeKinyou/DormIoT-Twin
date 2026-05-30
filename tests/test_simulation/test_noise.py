import statistics

from dormiot.simulation.noise import clamp, gaussian_noise, noisy_value


class TestGaussianNoise:
    def test_returns_float(self):
        assert isinstance(gaussian_noise(), float)

    def test_custom_mean_and_std(self):
        values = [gaussian_noise(mean=100, std=1) for _ in range(1000)]
        mean = statistics.mean(values)
        assert 98 < mean < 102  # 均值应在 100 附近


class TestClamp:
    def test_within_range(self):
        assert clamp(5, 0, 10) == 5

    def test_below_min(self):
        assert clamp(-1, 0, 10) == 0

    def test_above_max(self):
        assert clamp(15, 0, 10) == 10


class TestNoisyValue:
    def test_baseline_centered(self):
        values = [noisy_value(baseline=100, std=1) for _ in range(2000)]
        mean = statistics.mean(values)
        assert 98 < mean < 102

    def test_min_clamp(self):
        values = [noisy_value(baseline=0, std=10, min_val=0) for _ in range(1000)]
        assert all(v >= 0 for v in values)

    def test_max_clamp(self):
        values = [noisy_value(baseline=300, std=10, max_val=240) for _ in range(1000)]
        assert all(v <= 240 for v in values)

    def test_distribution_approximately_normal(self):
        """1000 次采样标准差应接近配置值"""
        values = [noisy_value(baseline=50, std=2) for _ in range(1000)]
        std = statistics.stdev(values)
        assert 1.5 < std < 2.5
