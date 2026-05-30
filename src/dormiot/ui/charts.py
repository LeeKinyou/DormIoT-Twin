from __future__ import annotations

from datetime import datetime


def power_trend_option(
    timestamps: list[str],
    values: list[float],
    title: str = "全校总功率趋势",
    overload_threshold: float = 800.0,
    illegal_threshold: float = 1500.0,
) -> dict:
    """生成全校总功率实时折线图 ECharts option"""
    return {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["总功率", "恶性负载线", "违章电器线"], "bottom": 0},
        "xAxis": {
            "type": "category",
            "data": timestamps,
            "axisLabel": {"rotate": 30},
        },
        "yAxis": {"type": "value", "name": "功率 (W)"},
        "series": [
            {
                "name": "总功率",
                "type": "line",
                "data": values,
                "smooth": True,
                "lineStyle": {"width": 2},
                "areaStyle": {"opacity": 0.15},
            },
            {
                "name": "恶性负载线",
                "type": "line",
                "data": [overload_threshold] * len(timestamps),
                "lineStyle": {"type": "dashed", "color": "#f59e0b"},
                "symbol": "none",
            },
            {
                "name": "违章电器线",
                "type": "line",
                "data": [illegal_threshold] * len(timestamps),
                "lineStyle": {"type": "dashed", "color": "#ef4444"},
                "symbol": "none",
            },
        ],
    }


def room_power_option(
    timestamps: list[str],
    values: list[float],
    room_id: str,
    overload_threshold: float = 800.0,
    illegal_threshold: float = 1500.0,
) -> dict:
    """生成单宿舍功率走势 ECharts option"""
    return {
        "title": {"text": f"房间 {room_id} 功率走势", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["功率", "恶性负载线", "违章电器线"], "bottom": 0},
        "xAxis": {
            "type": "category",
            "data": timestamps,
            "axisLabel": {"rotate": 30},
        },
        "yAxis": {"type": "value", "name": "功率 (W)"},
        "series": [
            {
                "name": "功率",
                "type": "line",
                "data": values,
                "smooth": True,
                "lineStyle": {"width": 2, "color": "#3b82f6"},
                "areaStyle": {"opacity": 0.1, "color": "#3b82f6"},
            },
            {
                "name": "恶性负载线",
                "type": "line",
                "data": [overload_threshold] * len(timestamps),
                "lineStyle": {"type": "dashed", "color": "#f59e0b"},
                "symbol": "none",
            },
            {
                "name": "违章电器线",
                "type": "line",
                "data": [illegal_threshold] * len(timestamps),
                "lineStyle": {"type": "dashed", "color": "#ef4444"},
                "symbol": "none",
            },
        ],
    }


def status_pie_option(normal: int, warning: int, alarm: int, offline: int = 0) -> dict:
    """设备状态分布饼图"""
    data = []
    if normal > 0:
        data.append({"value": normal, "name": "正常", "itemStyle": {"color": "#22c55e"}})
    if warning > 0:
        data.append({"value": warning, "name": "预警", "itemStyle": {"color": "#f59e0b"}})
    if alarm > 0:
        data.append({"value": alarm, "name": "告警", "itemStyle": {"color": "#ef4444"}})
    if offline > 0:
        data.append({"value": offline, "name": "离线", "itemStyle": {"color": "#94a3b8"}})
    return {
        "title": {"text": "设备状态分布", "left": "center"},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": data,
                "label": {"formatter": "{b}: {c} ({d}%)"},
            }
        ],
    }
