"""
阶段三测试：内存驱动的数据流（DataStore）
"""
import pytest
import time
import threading
from collections import deque


class TestDataStore:
    """测试数据存储层"""

    def test_import_data_store(self):
        """测试 DataStore 模块可以导入"""
        from dormiot.data_store import DataStore
        assert DataStore is not None

    def test_singleton_pattern(self):
        """测试 DataStore 是单例"""
        from dormiot.data_store import DataStore
        ds1 = DataStore()
        ds2 = DataStore()
        assert ds1 is ds2

    def test_initial_state_empty(self):
        """测试初始状态为空"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()
        assert ds.history_length == 0
        assert ds.latest_snapshot == {}

    def test_push_single_tick(self):
        """测试推入单个 tick 数据"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        tick_data = {
            "101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
            "102": {"power": 52.0, "voltage": 221.0, "smoke_density": 0.01, "status": "NORMAL"},
        }
        ds.push_tick(tick_data)
        assert ds.history_length == 1

    def test_push_multiple_ticks(self):
        """测试推入多个 tick 数据"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        for i in range(10):
            ds.push_tick({"101": {"power": 50.0 + i, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        assert ds.history_length == 10

    def test_max_history_60_seconds(self):
        """测试历史记录最多保留 60 秒（60 个 tick）"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        for i in range(70):
            ds.push_tick({"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        assert ds.history_length == 60

    def test_latest_snapshot(self):
        """测试 latest_snapshot 返回最新数据"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        ds.push_tick({"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        ds.push_tick({"101": {"power": 100.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})

        latest = ds.latest_snapshot
        assert latest["101"]["power"] == 100.0

    def test_get_room_history(self):
        """测试获取单个房间的历史数据"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        for i in range(5):
            ds.push_tick({
                "101": {"power": 50.0 + i * 10, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
                "102": {"power": 60.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
            })

        history = ds.get_room_history("101")
        assert len(history) == 5
        assert history[0]["power"] == 50.0
        assert history[-1]["power"] == 90.0

    def test_get_room_history_nonexistent(self):
        """测试获取不存在房间的历史返回空列表"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()
        assert ds.get_room_history("999") == []

    def test_get_power_array(self):
        """测试获取房间功率数组"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        for i in range(5):
            ds.push_tick({
                "101": {"power": 50.0 + i, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
            })

        powers = ds.get_power_array("101")
        assert powers == [50.0, 51.0, 52.0, 53.0, 54.0]

    def test_get_power_array_nonexistent(self):
        """测试获取不存在房间的功率数组返回空列表"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()
        assert ds.get_power_array("999") == []

    def test_thread_safety(self):
        """测试多线程并发写入不会崩溃"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        def writer(room_id, count):
            for i in range(count):
                ds.push_tick({
                    room_id: {"power": 50.0 + i, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
                })

        threads = [
            threading.Thread(target=writer, args=("101", 100)),
            threading.Thread(target=writer, args=("102", 100)),
            threading.Thread(target=writer, args=("103", 100)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不会崩溃，且数据量合理
        assert ds.history_length > 0

    def test_reset(self):
        """测试重置清空所有数据"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.push_tick({"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        ds.reset()
        assert ds.history_length == 0
        assert ds.latest_snapshot == {}

    def test_detect_power_spike(self):
        """测试功率飙升检测：2 秒内飙升超过 1000W"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        # 正常功率
        ds.push_tick({"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        ds.push_tick({"101": {"power": 55.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        # 功率飙升
        ds.push_tick({"101": {"power": 1850.0, "voltage": 210.0, "smoke_density": 0.02, "status": "ALARM_RESISTOR"}})

        spike = ds.detect_power_spike("101", threshold=1000, window=2)
        assert spike is True

    def test_detect_power_spike_no_spike(self):
        """测试正常波动不触发飙升检测"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        ds.push_tick({"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        ds.push_tick({"101": {"power": 52.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})
        ds.push_tick({"101": {"power": 55.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}})

        spike = ds.detect_power_spike("101", threshold=1000, window=2)
        assert spike is False

    def test_detect_power_spike_insufficient_data(self):
        """测试数据不足时不触发飙升检测"""
        from dormiot.data_store import DataStore
        ds = DataStore()
        ds.reset()

        ds.push_tick({"101": {"power": 1850.0, "voltage": 210.0, "smoke_density": 0.02, "status": "ALARM_RESISTOR"}})

        spike = ds.detect_power_spike("101", threshold=1000, window=2)
        assert spike is False


class TestBackgroundCollector:
    """测试后台数据采集线程"""

    def test_import_collector(self):
        """测试采集器可以导入"""
        from dormiot.data_store import BackgroundCollector
        assert BackgroundCollector is not None

    def test_collector_starts_and_stops(self):
        """测试采集器可以启动和停止"""
        from dormiot.data_store import BackgroundCollector, DataStore
        from dormiot.simulation.synthesizer import WaveformSynthesizer

        ds = DataStore()
        ds.reset()
        synth = WaveformSynthesizer()
        synth.reset()

        collector = BackgroundCollector(interval_s=0.1)
        collector.start()
        assert collector.is_running is True
        time.sleep(0.35)  # 等待采集几个 tick
        collector.stop()
        assert collector.is_running is False

        assert ds.history_length >= 2

    def test_collector_writes_to_datastore(self):
        """测试采集器正确写入 DataStore"""
        from dormiot.data_store import BackgroundCollector, DataStore
        from dormiot.simulation.synthesizer import WaveformSynthesizer

        ds = DataStore()
        ds.reset()
        synth = WaveformSynthesizer()
        synth.reset()

        collector = BackgroundCollector(interval_s=0.1)
        collector.start()
        time.sleep(0.35)
        collector.stop()

        latest = ds.latest_snapshot
        assert "101" in latest
        assert "power" in latest["101"]

    def test_collector_daemon_thread(self):
        """测试采集器是守护线程"""
        from dormiot.data_store import BackgroundCollector

        collector = BackgroundCollector(interval_s=0.1)
        collector.start()
        assert collector.thread.daemon is True
        collector.stop()

    def test_collector_publishes_to_mqtt(self):
        """测试采集器同时发布消息到 MQTT 仿真 Broker"""
        from dormiot.data_store import BackgroundCollector, DataStore
        from dormiot.simulation.synthesizer import WaveformSynthesizer
        from dormiot.protocol.mqtt_simulator import MQTTBroker

        ds = DataStore()
        ds.reset()
        synth = WaveformSynthesizer()
        synth.reset()
        MQTTBroker.reset()

        received_topics = []

        def on_message(topic, payload):
            received_topics.append(topic)

        broker = MQTTBroker()
        broker.subscribe("dormiot/campus/5/#", on_message)

        collector = BackgroundCollector(interval_s=0.1)
        collector.start()
        time.sleep(0.35)
        collector.stop()

        # 应该收到至少 6 个房间的消息
        assert len(received_topics) >= 6
        # Topic 格式应正确
        assert any("dormiot/campus/5/101/meter" in t for t in received_topics)
        assert any("dormiot/campus/5/106/meter" in t for t in received_topics)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
