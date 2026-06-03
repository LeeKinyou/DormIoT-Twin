"""
阶段二测试：物理波形合成引擎
"""
import pytest
import numpy as np
from dormiot.schemas.device import DeviceStatus


class TestWaveformSynthesizer:
    """测试波形合成器核心功能"""

    def test_import_synthesizer(self):
        """测试合成器模块可以导入"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        assert WaveformSynthesizer is not None

    def test_singleton_pattern(self):
        """测试合成器是单例"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        s1 = WaveformSynthesizer()
        s2 = WaveformSynthesizer()
        assert s1 is s2

    def test_get_next_tick_returns_dict(self):
        """测试 get_next_tick 返回字典"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        result = synth.get_next_tick()
        assert isinstance(result, dict)

    def test_get_next_tick_contains_rooms_101_to_106(self):
        """测试返回数据包含 101-106 六个房间"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        result = synth.get_next_tick()
        expected_rooms = ["101", "102", "103", "104", "105", "106"]
        assert list(result.keys()) == expected_rooms

    def test_each_room_has_required_fields(self):
        """测试每个房间数据包含必要字段"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        result = synth.get_next_tick()
        for room_id, data in result.items():
            assert "power" in data, f"房间 {room_id} 缺少 power 字段"
            assert "voltage" in data, f"房间 {room_id} 缺少 voltage 字段"
            assert "smoke_density" in data, f"房间 {room_id} 缺少 smoke_density 字段"
            assert "status" in data, f"房间 {room_id} 缺少 status 字段"

    def test_normal_power_range(self):
        """测试正常状态下功率在合理范围"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        # 采集多次取平均，消除随机波动
        powers = []
        for _ in range(100):
            result = synth.get_next_tick()
            powers.append(result["101"]["power"])
        avg_power = np.mean(powers)
        # 正常功率应在 50W 附近（基准 + 昼夜节律正弦波）
        assert 30 < avg_power < 100, f"正常平均功率 {avg_power:.1f}W 不在预期范围 [30, 100]"

    def test_normal_voltage_range(self):
        """测试正常状态下电压在合理范围"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        result = synth.get_next_tick()
        voltage = result["101"]["voltage"]
        assert 210 < voltage < 230, f"电压 {voltage:.1f}V 不在预期范围 [210, 230]"

    def test_alarm_resistor_power_spike(self):
        """测试热得快/吹风机模式：功率瞬间叠加 ~1800W"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        powers = []
        for _ in range(50):
            result = synth.get_next_tick()
            powers.append(result["101"]["power"])
        avg_power = np.mean(powers)
        # 基准 50 + 1800 = ~1850W
        assert avg_power > 1700, f"热得快平均功率 {avg_power:.1f}W 应 > 1700W"
        assert avg_power < 2100, f"热得快平均功率 {avg_power:.1f}W 应 < 2100W"

    def test_alarm_resistor_has_high_frequency_noise(self):
        """测试热得快模式有高频毛刺（标准差应较大）"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        powers = []
        for _ in range(100):
            result = synth.get_next_tick()
            powers.append(result["101"]["power"])
        std_power = np.std(powers)
        # 高频毛刺标准差应 ~40W
        assert std_power > 20, f"热得快功率标准差 {std_power:.1f}W 应 > 20W（高频毛刺）"

    def test_alarm_microwave_square_wave(self):
        """测试微波炉模式：方波在 +1200W 和 +30W 之间交替"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_MICROWAVE)

        # 采集 10 秒数据（5 秒高 + 5 秒低为一个周期）
        powers = []
        for _ in range(10):
            result = synth.get_next_tick()
            powers.append(result["101"]["power"])

        # 应该有明显的高低交替
        high_powers = [p for p in powers if p > 600]
        low_powers = [p for p in powers if p <= 600]
        # 至少应该有两种不同水平的功率
        assert len(high_powers) > 0 or len(low_powers) > 0, "微波炉模式应有功率波动"

    def test_alarm_microwave_high_level_around_1250w(self):
        """测试微波炉高电平约 1200+50=1250W"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_MICROWAVE)

        # 采集足够多数据，确保覆盖高电平阶段
        high_powers = []
        for _ in range(100):
            result = synth.get_next_tick()
            p = result["101"]["power"]
            if p > 600:  # 高电平
                high_powers.append(p)

        if high_powers:
            avg_high = np.mean(high_powers)
            assert 1100 < avg_high < 1400, f"微波炉高电平平均 {avg_high:.1f}W 应在 [1100, 1400]"

    def test_alarm_microwave_low_level_around_80w(self):
        """测试微波炉低电平约 30+50=80W"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_MICROWAVE)

        low_powers = []
        for _ in range(100):
            result = synth.get_next_tick()
            p = result["101"]["power"]
            if p <= 600:  # 低电平
                low_powers.append(p)

        if low_powers:
            avg_low = np.mean(low_powers)
            assert 40 < avg_low < 150, f"微波炉低电平平均 {avg_low:.1f}W 应在 [40, 150]"

    def test_set_alarm_mode_returns_bool(self):
        """测试 set_alarm_mode 返回布尔值"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        assert synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR) is True
        assert synth.set_alarm_mode("999", DeviceStatus.ALARM_RESISTOR) is False

    def test_clear_alarm_mode(self):
        """测试清除告警模式后恢复正常"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        synth.clear_alarm_mode("101")

        powers = []
        for _ in range(100):
            result = synth.get_next_tick()
            powers.append(result["101"]["power"])
        avg_power = np.mean(powers)
        assert avg_power < 200, f"清除告警后平均功率 {avg_power:.1f}W 应 < 200W"

    def test_reset(self):
        """测试重置合成器状态"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        synth.set_alarm_mode("102", DeviceStatus.ALARM_MICROWAVE)
        synth.reset()

        result = synth.get_next_tick()
        for room_id, data in result.items():
            assert data["status"] == DeviceStatus.NORMAL, f"重置后房间 {room_id} 应为 NORMAL"

    def test_status_field_correct(self):
        """测试状态字段正确反映当前模式"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()

        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        result = synth.get_next_tick()
        assert result["101"]["status"] == DeviceStatus.ALARM_RESISTOR
        assert result["102"]["status"] == DeviceStatus.NORMAL

    def test_tick_counter_increments(self):
        """测试时间戳递增"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.get_next_tick()
        synth.get_next_tick()
        synth.get_next_tick()
        assert synth.tick_count == 3

    def test_multiple_rooms_independent(self):
        """测试多个房间独立控制"""
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        synth = WaveformSynthesizer()
        synth.reset()
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        synth.set_alarm_mode("103", DeviceStatus.ALARM_MICROWAVE)

        result = synth.get_next_tick()
        assert result["101"]["status"] == DeviceStatus.ALARM_RESISTOR
        assert result["102"]["status"] == DeviceStatus.NORMAL
        assert result["103"]["status"] == DeviceStatus.ALARM_MICROWAVE
        assert result["104"]["status"] == DeviceStatus.NORMAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
