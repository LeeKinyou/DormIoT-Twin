"""
阶段四测试：赛博朋克 UI 辅助函数（纯逻辑，不依赖 Streamlit）
"""
import pytest
from dormiot.ui.helpers import (
    get_room_color,
    build_power_chart,
    build_room_grid_data,
    ALERT_LOG_KEY,
)


class TestRoomColor:
    """测试房间颜色逻辑"""

    def test_normal_room_green(self):
        color = get_room_color(50.0)
        assert color == "#00ff41"

    def test_low_power_green(self):
        color = get_room_color(100.0)
        assert color == "#00ff41"

    def test_threshold_power_green(self):
        color = get_room_color(1500.0)
        assert color == "#00ff41"

    def test_over_threshold_red(self):
        color = get_room_color(1501.0)
        assert color == "#ff073a"

    def test_high_power_red(self):
        color = get_room_color(2000.0)
        assert color == "#ff073a"


class TestRoomGridData:
    """测试 6 宫格数据构建"""

    def test_returns_six_rooms(self):
        snapshot = {
            str(i): {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}
            for i in range(101, 107)
        }
        grid = build_room_grid_data(snapshot)
        assert len(grid) == 6

    def test_room_ids_101_to_106(self):
        snapshot = {
            str(i): {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}
            for i in range(101, 107)
        }
        grid = build_room_grid_data(snapshot)
        room_ids = [r["room_id"] for r in grid]
        assert room_ids == ["101", "102", "103", "104", "105", "106"]

    def test_normal_room_has_green_color(self):
        snapshot = {
            "101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
        }
        grid = build_room_grid_data(snapshot)
        assert grid[0]["color"] == "#00ff41"

    def test_alarm_room_has_red_color(self):
        snapshot = {
            "101": {"power": 1850.0, "voltage": 210.0, "smoke_density": 0.02, "status": "ALARM_RESISTOR"},
        }
        grid = build_room_grid_data(snapshot)
        assert grid[0]["color"] == "#ff073a"

    def test_missing_room_defaults(self):
        snapshot = {}
        grid = build_room_grid_data(snapshot)
        assert len(grid) == 6
        for room in grid:
            assert room["power"] == 0.0
            assert room["color"] == "#00ff41"

    def test_power_value_passed_through(self):
        snapshot = {
            "101": {"power": 123.4, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"},
        }
        grid = build_room_grid_data(snapshot)
        assert grid[0]["power"] == 123.4


class TestPowerChart:
    """测试 Plotly 功率图配置"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        fig = build_power_chart(["10:00:00", "10:00:01"], [50.0, 52.0], room_id="101")
        assert isinstance(fig, go.Figure)

    def test_has_traces(self):
        fig = build_power_chart(["10:00:00"], [50.0])
        assert len(fig.data) > 0

    def test_has_title(self):
        fig = build_power_chart(["10:00:00"], [50.0], room_id="101")
        assert "101" in fig.layout.title.text

    def test_dark_background(self):
        fig = build_power_chart(["10:00:00"], [50.0])
        assert fig.layout.paper_bgcolor == "#0a0a0f"
        assert fig.layout.plot_bgcolor == "#0a0a0f"

    def test_empty_data(self):
        fig = build_power_chart([], [])
        assert isinstance(fig, type(fig))

    def test_cyan_line_color(self):
        fig = build_power_chart(["10:00:00"], [50.0])
        assert fig.data[0].line.color == "#00d4ff"


class TestAlertLogKey:
    """测试告警日志 key 常量"""

    def test_alert_log_key_is_string(self):
        assert isinstance(ALERT_LOG_KEY, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
