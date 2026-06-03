"""UI 辅助函数模块

提供纯函数，用于准备渲染数据、生成图表配置和管理颜色映射。
所有函数均无副作用，便于单元测试。
"""
from __future__ import annotations

import time
from typing import Any

import plotly.graph_objects as go

# ── 政企科技风色彩体系（绿色主题）──
# 背景层
COLOR_BG_MAIN = "#0a1a12"          # 主背景（深墨绿）
COLOR_BG_SIDEBAR = "#0d1f16"       # 侧边栏
COLOR_BG_CARD = "#132a1e"          # 卡片背景（暗绿灰）
COLOR_BORDER = "#1e3a2a"           # 墨绿边框

# 主色层
COLOR_PRIMARY = "#238E54"          # 主色调（科技绿）
COLOR_PRIMARY_LIGHT = "#2ca86a"    # 亮翠绿（hover/选中）
COLOR_PRIMARY_HIGHLIGHT = "#34c77b"  # 高亮绿

# 状态层
COLOR_SUCCESS = "#27ae60"          # 翡翠绿（正常/成功）
COLOR_WARNING = "#f39c12"          # 琥珀黄（预警）
COLOR_ALARM = "#e74c3c"            # 柔和红（告警）

# 文字层
COLOR_TEXT_PRIMARY = "#d4e6df"     # 薄荷白（主文字）
COLOR_TEXT_SECONDARY = "#7f9a8e"   # 绿灰（辅助文字）

# 兼容旧代码的别名
COLOR_NEON_GREEN = COLOR_PRIMARY
COLOR_NEON_RED = COLOR_ALARM
COLOR_CYAN = COLOR_PRIMARY_LIGHT

# 阈值
POWER_ALARM_THRESHOLD = 1500.0     # 告警阈值
POWER_WARNING_THRESHOLD = 800.0    # 预警阈值


def get_room_color(power: float) -> str:
    """根据功率返回房间状态颜色

    Args:
        power: 当前功率值 (W)

    Returns:
        颜色代码：正常=科技绿, 预警=琥珀黄, 告警=柔和红
    """
    if power > POWER_ALARM_THRESHOLD:
        return COLOR_ALARM
    elif power > POWER_WARNING_THRESHOLD:
        return COLOR_WARNING
    return COLOR_PRIMARY


def get_room_bg_color(power: float) -> str:
    """根据功率返回房间卡片背景色（带透明度）"""
    if power > POWER_ALARM_THRESHOLD:
        return "rgba(231, 76, 60, 0.15)"
    elif power > POWER_WARNING_THRESHOLD:
        return "rgba(243, 156, 18, 0.1)"
    return COLOR_BG_CARD


def get_status_text(power: float) -> str:
    """根据功率返回状态文本"""
    if power > POWER_ALARM_THRESHOLD:
        return "⚠ 告警"
    elif power > POWER_WARNING_THRESHOLD:
        return "⚡ 预警"
    return "● 正常"


def build_room_grid_data(snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """构建房间网格数据

    Args:
        snapshot: {room_id: {power, voltage, smoke_density, status}}

    Returns:
        房间信息列表，包含 id/power/voltage/smoke_density/color/bg_color/status_text
    """
    rooms = []
    for room_id in ["101", "102", "103", "104", "105", "106"]:
        data = snapshot.get(room_id, {})
        power = data.get("power", 0.0)
        rooms.append({
            "id": room_id,
            "power": power,
            "voltage": data.get("voltage", 0.0),
            "smoke_density": data.get("smoke_density", 0.0),
            "color": get_room_color(power),
            "bg_color": get_room_bg_color(power),
            "status_text": get_status_text(power),
        })
    return rooms


def build_power_chart(
    timestamps: list[str],
    values: list[float],
    room_id: str | None = None,
    threshold_warning: float = POWER_WARNING_THRESHOLD,
    threshold_alarm: float = POWER_ALARM_THRESHOLD,
) -> go.Figure:
    """构建功率波形图（Plotly）

    Args:
        timestamps: 时间标签列表（如 ["14:32:01", "14:32:02", ...]）
        values: 功率值列表
        room_id: 房间号（可选，显示在标题中）
        threshold_warning: 预警阈值线
        threshold_alarm: 告警阈值线

    Returns:
        Plotly Figure 对象
    """
    title = f"房间 {room_id} 实时功率" if room_id else "实时功率监控"
    line_color = COLOR_ALARM if (values and max(values) > threshold_alarm) else COLOR_PRIMARY

    fig = go.Figure()

    # 渐变填充区域
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode="lines",
        name="功率 (W)",
        line=dict(color=line_color, width=2, shape="hv"),
        fill="tozeroy",
        fillcolor=f"rgba(35, 142, 84, 0.2)" if line_color == COLOR_PRIMARY else f"rgba(231, 76, 60, 0.15)",
    ))

    # 预警阈值线
    fig.add_hline(
        y=threshold_warning,
        line_dash="dash",
        line_color=COLOR_WARNING,
        opacity=0.6,
        annotation_text=f"预警 {threshold_warning:.0f}W",
        annotation_font_color=COLOR_WARNING,
    )

    # 告警阈值线
    fig.add_hline(
        y=threshold_alarm,
        line_dash="dash",
        line_color=COLOR_ALARM,
        opacity=0.6,
        annotation_text=f"告警 {threshold_alarm:.0f}W",
        annotation_font_color=COLOR_ALARM,
    )

    fig.update_layout(
        title=dict(text=title, font=dict(color=COLOR_TEXT_PRIMARY, size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLOR_BG_MAIN,
        font=dict(family="Inter, Noto Sans SC, sans-serif", color=COLOR_TEXT_PRIMARY),
        xaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
            ticksuffix=" W",
            range=[0, max(max(values) * 1.2, threshold_alarm * 1.3) if values else 2000],
        ),
        margin=dict(l=50, r=30, t=40, b=30),
        showlegend=False,
        height=280,
    )

    return fig


def build_alarm_log_entry(
    room_id: str,
    power_array: list[float],
    ai_diagnosis: str | None = None,
) -> dict[str, Any]:
    """构建告警日志条目

    Args:
        room_id: 房间号
        power_array: 最近的功率数据数组
        ai_diagnosis: AI 研判结果（可选）

    Returns:
        告警日志字典，包含 room_id/power/timestamp/diagnosis
    """
    current_power = power_array[-1] if power_array else 0.0
    return {
        "room_id": room_id,
        "power": current_power,
        "timestamp": time.strftime("%H:%M:%S"),
        "diagnosis": ai_diagnosis,
    }


def format_mqtt_log_entry(topic: str, payload: dict[str, Any]) -> str:
    """格式化 MQTT 日志条目用于 UI 显示

    Args:
        topic: MQTT Topic
        payload: 消息载荷

    Returns:
        格式化的日志字符串
    """
    power = payload.get("power", 0)
    ts = time.strftime("%H:%M:%S")
    if power > POWER_ALARM_THRESHOLD:
        return f"⚠ {ts}  → {topic}  | {power:.1f}W"
    return f"  {ts}  → {topic}  | {power:.1f}W"
