"""赛博朋克 UI 辅助函数（纯逻辑，不依赖 Streamlit）

将渲染数据准备逻辑抽离为纯函数，方便单元测试。
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

# ── 赛博朋克色板 ──
COLOR_NEON_GREEN = "#00ff41"   # 幽绿色（正常）
COLOR_NEON_RED = "#ff073a"     # 警戒红（告警）
COLOR_DARK_BG = "#0a0a0f"     # 深色背景
COLOR_PANEL_BG = "#111118"    # 面板背景
COLOR_BORDER = "#1a1a2e"      # 边框色
COLOR_TEXT = "#e0e0e0"        # 文字色
COLOR_CYAN = "#00d4ff"        # 青色高亮

# ── 告警日志 session key ──
ALERT_LOG_KEY = "alert_logs"

# ── 功率阈值 ──
POWER_ALARM_THRESHOLD = 1500.0


def get_room_color(power: float) -> str:
    """根据功率返回房间背景色

    Args:
        power: 当前功率 (W)

    Returns:
        色值字符串：绿色（正常）或红色（告警）
    """
    if power > POWER_ALARM_THRESHOLD:
        return COLOR_NEON_RED
    return COLOR_NEON_GREEN


def build_room_grid_data(
    snapshot: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """构建 6 宫格数据

    Args:
        snapshot: DataStore.latest_snapshot 格式的数据

    Returns:
        6 个元素的列表，每个包含 room_id/power/voltage/smoke_density/status/color
    """
    rooms = []
    for room_id in ["101", "102", "103", "104", "105", "106"]:
        data = snapshot.get(room_id, {})
        power = data.get("power", 0.0)
        rooms.append({
            "room_id": room_id,
            "power": power,
            "voltage": data.get("voltage", 0.0),
            "smoke_density": data.get("smoke_density", 0.0),
            "status": data.get("status", "NORMAL"),
            "color": get_room_color(power),
        })
    return rooms


def build_power_chart(
    timestamps: list[str],
    values: list[float],
    room_id: str | None = None,
) -> go.Figure:
    """构建 Plotly 实时功率图（赛博朋克风格）

    Args:
        timestamps: 时间标签列表
        values: 功率值列表
        room_id: 房间号（用于标题，可选）

    Returns:
        Plotly Figure 对象
    """
    title = f"房间 {room_id} 实时功率" if room_id else "实时功率监控"

    if not timestamps:
        timestamps = ["--:--:--"]
        values = [0.0]

    fig = go.Figure()

    # 添加渐变填充区域
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.15)',
        line=dict(color=COLOR_CYAN, width=2),
        mode='lines',
        name='功率',
        hovertemplate='%{x}<br>功率: %{y:.1f}W<extra></extra>',
    ))

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=COLOR_CYAN, size=14),
            x=0.5,
        ),
        paper_bgcolor=COLOR_DARK_BG,
        plot_bgcolor=COLOR_DARK_BG,
        font=dict(color=COLOR_TEXT, family="Courier New"),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_BORDER,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="功率 (W)",
            showgrid=True,
            gridcolor=COLOR_BORDER,
        ),
        margin=dict(l=50, r=30, t=40, b=30),
        showlegend=False,
    )

    return fig


def build_alarm_log_entry(
    room_id: str,
    power_array: list[float],
    ai_diagnosis: str | None = None,
) -> dict[str, Any]:
    """构建一条告警日志条目

    Args:
        room_id: 房间号
        power_array: 功率数组
        ai_diagnosis: AI 研判结果（可选）

    Returns:
        告警日志字典
    """
    from datetime import datetime

    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "room_id": room_id,
        "current_power": power_array[-1] if power_array else 0.0,
        "ai_diagnosis": ai_diagnosis or "等待 AI 研判...",
    }
