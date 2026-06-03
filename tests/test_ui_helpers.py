"""阶段四测试：政企科技风 UI 辅助函数

测试颜色映射、网格数据构建、图表配置生成等纯函数。
"""
import pytest
from unittest.mock import patch
import plotly.graph_objects as go

from dormiot.ui.helpers import (
    COLOR_PRIMARY,
    COLOR_ALARM,
    COLOR_WARNING,
    COLOR_SUCCESS,
    COLOR_BG_MAIN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_BORDER,
    COLOR_BG_CARD,
    COLOR_PRIMARY_LIGHT,
    COLOR_PRIMARY_HIGHLIGHT,
    COLOR_CYAN,
    COLOR_NEON_GREEN,
    COLOR_NEON_RED,
    POWER_ALARM_THRESHOLD,
    POWER_WARNING_THRESHOLD,
    get_room_color,
    get_room_bg_color,
    get_status_text,
    build_room_grid_data,
    build_power_chart,
    build_alarm_log_entry,
    format_mqtt_log_entry,
)


# ── 配色常量 ──


class TestColorConstants:
    def test_primary_green(self):
        """主色调是科技绿 #238E54"""
        assert COLOR_PRIMARY == "#238E54"

    def test_alarm_color_soft_red(self):
        """告警色是柔和红 #e74c3c"""
        assert COLOR_ALARM == "#e74c3c"

    def test_warning_color_amber(self):
        """预警色是琥珀黄 #f39c12"""
        assert COLOR_WARNING == "#f39c12"

    def test_success_color_emerald(self):
        """成功色是翡翠绿 #27ae60"""
        assert COLOR_SUCCESS == "#27ae60"

    def test_bg_main_dark_green(self):
        """主背景色是深墨绿"""
        assert COLOR_BG_MAIN == "#0a1a12"

    def test_text_primary_mint_white(self):
        """主文字色是薄荷白"""
        assert COLOR_TEXT_PRIMARY == "#d4e6df"

    def test_text_secondary_green_gray(self):
        """辅助文字色是绿灰"""
        assert COLOR_TEXT_SECONDARY == "#7f9a8e"

    def test_border_green_gray(self):
        """边框色是墨绿边框"""
        assert COLOR_BORDER == "#1e3a2a"

    def test_card_bg_dark_green(self):
        """卡片背景是暗绿灰"""
        assert COLOR_BG_CARD == "#132a1e"

    def test_compatibility_aliases(self):
        """旧代码别名仍然可用"""
        assert COLOR_NEON_GREEN == COLOR_PRIMARY
        assert COLOR_NEON_RED == COLOR_ALARM
        assert COLOR_CYAN == COLOR_PRIMARY_LIGHT


# ── get_room_color ──


class TestRoomColor:
    def test_normal_room_green(self):
        """正常功率时返回科技绿"""
        assert get_room_color(50.0) == COLOR_PRIMARY

    def test_low_power_green(self):
        """低功率时返回科技绿"""
        assert get_room_color(100.0) == COLOR_PRIMARY

    def test_threshold_power_green(self):
        """刚好在预警阈值时返回科技绿"""
        assert get_room_color(POWER_WARNING_THRESHOLD) == COLOR_PRIMARY

    def test_warning_zone_amber(self):
        """预警区间返回琥珀黄"""
        assert get_room_color(900.0) == COLOR_WARNING

    def test_over_threshold_red(self):
        """超过告警阈值时返回柔和红"""
        assert get_room_color(1600.0) == COLOR_ALARM

    def test_high_power_red(self):
        """高功率时返回柔和红"""
        assert get_room_color(2500.0) == COLOR_ALARM


# ── get_room_bg_color ──


class TestRoomBgColor:
    def test_normal_bg(self):
        assert get_room_bg_color(50.0) == COLOR_BG_CARD

    def test_warning_bg(self):
        assert get_room_bg_color(900.0) == "rgba(243, 156, 18, 0.1)"

    def test_alarm_bg(self):
        assert get_room_bg_color(1600.0) == "rgba(231, 76, 60, 0.15)"


# ── get_status_text ──


class TestStatusText:
    def test_normal(self):
        assert get_status_text(50.0) == "● 正常"

    def test_warning(self):
        assert get_status_text(900.0) == "⚡ 预警"

    def test_alarm(self):
        assert get_status_text(1600.0) == "⚠ 告警"


# ── build_room_grid_data ──


class TestRoomGridData:
    def test_returns_six_rooms(self):
        """应返回 6 个房间"""
        rooms = build_room_grid_data({})
        assert len(rooms) == 6

    def test_room_ids_101_to_106(self):
        """房间号从 101 到 106"""
        rooms = build_room_grid_data({})
        ids = [r["id"] for r in rooms]
        assert ids == ["101", "102", "103", "104", "105", "106"]

    def test_normal_room_has_green_color(self):
        """正常房间的颜色是科技绿"""
        snapshot = {"101": {"power": 50.0, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}}
        rooms = build_room_grid_data(snapshot)
        assert rooms[0]["color"] == COLOR_PRIMARY

    def test_alarm_room_has_red_color(self):
        """告警房间的颜色是柔和红"""
        snapshot = {"102": {"power": 1800.0, "voltage": 210.0, "smoke_density": 0.02, "status": "ALARM"}}
        rooms = build_room_grid_data(snapshot)
        room_102 = [r for r in rooms if r["id"] == "102"][0]
        assert room_102["color"] == COLOR_ALARM

    def test_missing_room_defaults(self):
        """缺失数据的房间使用默认值"""
        rooms = build_room_grid_data({})
        for room in rooms:
            assert room["power"] == 0.0
            assert room["color"] == COLOR_PRIMARY

    def test_power_value_passed_through(self):
        """功率值正确传递"""
        snapshot = {"101": {"power": 123.4, "voltage": 220.0, "smoke_density": 0.01, "status": "NORMAL"}}
        rooms = build_room_grid_data(snapshot)
        assert rooms[0]["power"] == 123.4

    def test_voltage_and_smoke_passed_through(self):
        """电压和烟雾浓度正确传递"""
        snapshot = {"101": {"power": 50.0, "voltage": 225.0, "smoke_density": 0.05, "status": "NORMAL"}}
        rooms = build_room_grid_data(snapshot)
        assert rooms[0]["voltage"] == 225.0
        assert rooms[0]["smoke_density"] == 0.05


# ── build_power_chart ──


class TestPowerChart:
    def test_returns_figure(self):
        """应返回 Plotly Figure"""
        fig = build_power_chart(["14:00", "14:01"], [50, 52])
        assert isinstance(fig, go.Figure)

    def test_has_traces(self):
        """图表应有数据序列"""
        fig = build_power_chart(["14:00", "14:01"], [50, 52])
        assert len(fig.data) > 0

    def test_has_title(self):
        """图表应有标题"""
        fig = build_power_chart(["14:00", "14:01"], [50, 52], room_id="101")
        assert "101" in fig.layout.title.text

    def test_dark_background(self):
        """图表应使用深色背景"""
        fig = build_power_chart(["14:00", "14:01"], [50, 52])
        assert fig.layout.plot_bgcolor == COLOR_BG_MAIN

    def test_empty_data(self):
        """空数据不应崩溃"""
        fig = build_power_chart([], [])
        assert isinstance(fig, go.Figure)

    def test_primary_line_color(self):
        """正常功率时线条为科技绿"""
        fig = build_power_chart(["14:00", "14:01"], [50, 52])
        assert fig.data[0].line.color == COLOR_PRIMARY

    def test_alarm_line_color(self):
        """超限时线条变为柔和红"""
        fig = build_power_chart(["14:00", "14:01"], [50, 1800])
        assert fig.data[0].line.color == COLOR_ALARM


# ── build_alarm_log_entry ──


class TestAlarmLogEntry:
    def test_basic_entry(self):
        """基本告警日志条目"""
        entry = build_alarm_log_entry("101", [50.0, 1800.0])
        assert entry["room_id"] == "101"
        assert entry["power"] == 1800.0
        assert "timestamp" in entry

    def test_with_ai_diagnosis(self):
        """带 AI 研判的告警日志条目"""
        entry = build_alarm_log_entry("102", [50.0, 1850.0], ai_diagnosis="疑似热得快")
        assert entry["diagnosis"] == "疑似热得快"

    def test_empty_power_array(self):
        """空功率数组"""
        entry = build_alarm_log_entry("103", [])
        assert entry["power"] == 0.0


# ── format_mqtt_log_entry ──


class TestMQTTLogEntry:
    def test_normal_message(self):
        """正常消息格式化"""
        result = format_mqtt_log_entry("dormiot/campus/5/101/meter", {"power": 50.0})
        assert "dormiot/campus/5/101/meter" in result
        assert "50.0" in result

    def test_alarm_message_has_warning_icon(self):
        """告警消息带 ⚠ 图标"""
        result = format_mqtt_log_entry("dormiot/campus/5/102/meter", {"power": 1800.0})
        assert "⚠" in result
