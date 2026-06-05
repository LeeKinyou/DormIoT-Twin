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


def get_trend_info(
    power_history: list[float], window: int = 5
) -> tuple[str, str, float]:
    """计算功率趋势（与前一个窗口对比）

    Args:
        power_history: 功率历史数组
        window: 对比窗口大小

    Returns:
        (arrow, color, delta) 元组：
        - arrow: "↑" / "↓" / "→"
        - color: 颜色代码
        - delta: 变化量 (W)
    """
    if len(power_history) < window + 1:
        return "→", COLOR_TEXT_SECONDARY, 0.0

    current = power_history[-1]
    prev_avg = sum(power_history[-(window + 1):-1]) / window
    delta = current - prev_avg

    if delta > 5:
        return "↑", COLOR_ALARM, delta
    elif delta < -5:
        return "↓", COLOR_SUCCESS, delta
    return "→", COLOR_TEXT_SECONDARY, delta


def build_room_grid_data(
    snapshot: dict[str, dict[str, Any]],
    room_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """构建房间网格数据

    Args:
        snapshot: {room_id: {power, voltage, smoke_density, status}}
        room_ids: 房间 ID 列表，为 None 时使用默认 6 个房间

    Returns:
        房间信息列表，包含 id/power/voltage/smoke_density/color/bg_color/status_text
    """
    if room_ids is None:
        room_ids = ["101", "102", "103", "104", "105", "106"]
    rooms = []
    for room_id in room_ids:
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
    """构建功率波形图（Plotly），带异常区间标注

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

    # 异常区间标注（告警区域红色背景）
    if values and len(values) > 1:
        in_alarm = False
        alarm_start = 0
        for i, v in enumerate(values):
            if v > threshold_alarm and not in_alarm:
                in_alarm = True
                alarm_start = i
            elif v <= threshold_alarm and in_alarm:
                in_alarm = False
                fig.add_vrect(
                    x0=timestamps[alarm_start], x1=timestamps[i],
                    fillcolor=COLOR_ALARM, opacity=0.1,
                    layer="below", line_width=0,
                )
        # 如果结尾仍在告警
        if in_alarm:
            fig.add_vrect(
                x0=timestamps[alarm_start], x1=timestamps[-1],
                fillcolor=COLOR_ALARM, opacity=0.1,
                layer="below", line_width=0,
            )

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


def build_history_trend_chart(
    rooms_history: dict[str, list[float]],
    max_points: int = 60,
    timestamps: list[str] | None = None,
) -> go.Figure:
    """构建多房间历史趋势对比图

    Args:
        rooms_history: {room_id: [power_values]} 字典
        max_points: 最多显示的数据点数
        timestamps: X 轴时间标签列表（可选）

    Returns:
        Plotly Figure 对象
    """
    fig = go.Figure()

    colors = [COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_PRIMARY_HIGHLIGHT,
              COLOR_WARNING, COLOR_ALARM, COLOR_SUCCESS]

    for i, (room_id, history) in enumerate(rooms_history.items()):
        if not history:
            continue

        # 只取最近的数据点
        recent = history[-max_points:]
        color = colors[i % len(colors)]

        # 使用时间戳或索引
        x_values = timestamps[-max_points:] if timestamps else None

        fig.add_trace(go.Scatter(
            x=x_values,
            y=recent,
            name=f"Room {room_id}",
            line=dict(color=color, width=1.5),
            mode="lines",
        ))

    fig.update_layout(
        title=dict(
            text="多房间功率趋势对比",
            font=dict(color=COLOR_TEXT_PRIMARY, size=14),
        ),
        xaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10, color=COLOR_TEXT_SECONDARY),
        ),
        yaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
            ticksuffix=" W",
            tickfont=dict(size=10, color=COLOR_TEXT_SECONDARY),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLOR_BG_MAIN,
        font=dict(family="Inter, Noto Sans SC, sans-serif", color=COLOR_TEXT_PRIMARY),
        height=250,
        margin=dict(l=50, r=30, t=40, b=30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9),
        ),
    )

    return fig


def build_energy_statistics_chart(rooms_history: dict[str, list[float]]) -> go.Figure:
    """构建能耗统计图表

    Args:
        rooms_history: {room_id: [power_values]} 字典

    Returns:
        Plotly Figure 对象，展示各房间能耗统计
    """
    # 计算统计数据
    room_ids = []
    avg_powers = []
    max_powers = []
    total_powers = []

    for room_id, history in rooms_history.items():
        if not history:
            continue

        room_ids.append(room_id)
        avg_powers.append(sum(history) / len(history))
        max_powers.append(max(history))
        total_powers.append(sum(history))

    if not room_ids:
        return go.Figure()

    # 创建柱状图
    fig = go.Figure()

    # 平均功率
    fig.add_trace(go.Bar(
        name='平均功率',
        x=room_ids,
        y=avg_powers,
        marker_color=COLOR_PRIMARY,
        opacity=0.8,
    ))

    # 最大功率
    fig.add_trace(go.Bar(
        name='最大功率',
        x=room_ids,
        y=max_powers,
        marker_color=COLOR_ALARM,
        opacity=0.6,
    ))

    fig.update_layout(
        title=dict(
            text="能耗统计分析",
            font=dict(color=COLOR_TEXT_PRIMARY, size=14),
        ),
        xaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=False,
            tickfont=dict(size=10, color=COLOR_TEXT_SECONDARY),
        ),
        yaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
            ticksuffix=" W",
            tickfont=dict(size=10, color=COLOR_TEXT_SECONDARY),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLOR_BG_MAIN,
        font=dict(family="Inter, Noto Sans SC, sans-serif", color=COLOR_TEXT_PRIMARY),
        height=250,
        margin=dict(l=50, r=30, t=40, b=30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9),
        ),
        barmode='group',
    )

    return fig


def build_ai_reasoning_chart(waveform_type: str, features: dict[str, float], diagnosis: str) -> go.Figure:
    """构建 AI 推理流程图

    Args:
        waveform_type: 波形分类（尖峰/方波/持续高频/正常）
        features: 波形特征字典
        diagnosis: AI 研判结果

    Returns:
        Plotly Figure 对象，展示推理流程
    """
    fig = go.Figure()

    # 定义流程步骤
    steps = [
        {"x": 0, "y": 0.5, "text": "📊 感知层", "detail": f"采样 {int(features.get('count', 0))} 点", "color": COLOR_PRIMARY},
        {"x": 1.5, "y": 0.5, "text": "🔍 特征提取", "detail": f"均值: {features.get('mean', 0):.0f}W\n标准差: {features.get('std', 0):.1f}", "color": COLOR_PRIMARY_LIGHT},
        {"x": 3, "y": 0.5, "text": "🤖 LLM 推理", "detail": "LangChain + OpenAI", "color": COLOR_PRIMARY_HIGHLIGHT},
        {"x": 4.5, "y": 0.5, "text": "📋 研判输出", "detail": waveform_type, "color": COLOR_ALARM if waveform_type != "正常" else COLOR_SUCCESS},
    ]

    # 绘制流程框
    for step in steps:
        # 背景框
        fig.add_shape(
            type="rect",
            x0=step["x"] - 0.5, y0=step["y"] - 0.3,
            x1=step["x"] + 0.5, y1=step["y"] + 0.3,
            fillcolor=step["color"],
            opacity=0.3,
            line=dict(color=step["color"], width=2),
        )

        # 主标题
        fig.add_annotation(
            x=step["x"], y=step["y"] + 0.1,
            text=step["text"],
            showarrow=False,
            font=dict(size=12, color="white"),
        )

        # 详情
        fig.add_annotation(
            x=step["x"], y=step["y"] - 0.15,
            text=step["detail"],
            showarrow=False,
            font=dict(size=8, color=COLOR_TEXT_SECONDARY),
        )

    # 绘制箭头连接
    for i in range(len(steps) - 1):
        fig.add_annotation(
            x=steps[i + 1]["x"] - 0.5,
            y=steps[i]["y"],
            ax=steps[i]["x"] + 0.5,
            ay=steps[i]["y"],
            xref="x", yref="y",
            axref="x", ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowcolor=COLOR_TEXT_SECONDARY,
        )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-1, 5.5]),
        yaxis=dict(visible=False, range=[-0.1, 1]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=120,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )

    return fig


def extract_waveform_features(data: list[float] | Any) -> dict[str, float]:
    """提取波形统计特征

    Args:
        data: 功率数据数组（list 或 numpy array）

    Returns:
        特征字典，包含 mean/std/max/min/ptp/count
    """
    import numpy as np

    arr = np.array(data) if not isinstance(data, np.ndarray) else data

    if len(arr) == 0:
        return {"mean": 0.0, "std": 0.0, "max": 0.0, "min": 0.0, "ptp": 0.0, "count": 0}

    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "max": float(np.max(arr)),
        "min": float(np.min(arr)),
        "ptp": float(np.ptp(arr)),
        "count": len(arr),
    }


def build_floor_plan_chart(rooms_data: list[dict[str, Any]], rooms_per_row: int = 6) -> go.Figure:
    """构建单层宿舍平面图（Plotly），支持 hover 交互

    Args:
        rooms_data: 房间数据列表，由 build_room_grid_data() 生成
        rooms_per_row: 每行显示的房间数

    Returns:
        Plotly Figure 对象，包含该层所有房间的矩形、标注和 hover 信息
    """
    if not rooms_data:
        return go.Figure()

    # 计算布局
    n_cols = min(rooms_per_row, len(rooms_data))
    n_rows = (len(rooms_data) + n_cols - 1) // n_cols

    fig = go.Figure()

    # 用 Scatter 放置不可见的 hover 点（在每个房间中心）
    hover_x = []
    hover_y = []
    hover_text = []
    hover_marker_colors = []

    for i, room in enumerate(rooms_data):
        col = i % n_cols
        row = i // n_cols
        x = col
        y = n_rows - 1 - row  # 从上到下
        color = room["color"]

        # 绘制房间方块
        fig.add_shape(
            type="rect",
            x0=x, y0=y, x1=x+0.9, y1=y+0.9,
            fillcolor=color,
            opacity=0.7,
            line=dict(color=color, width=1),
        )

        # 添加房间号
        fig.add_annotation(
            x=x+0.45, y=y+0.6,
            text=f"<b>{room['id']}</b>",
            showarrow=False,
            font=dict(size=10, color="white"),
        )

        # 添加功率数值
        fig.add_annotation(
            x=x+0.45, y=y+0.3,
            text=f"{room['power']:.0f}W",
            showarrow=False,
            font=dict(size=8, color="white"),
        )

        # 收集 hover 数据
        hover_x.append(x + 0.45)
        hover_y.append(y + 0.45)
        status = get_status_text(room["power"])
        hover_text.append(
            f"<b>Room {room['id']}</b><br>"
            f"功率: {room['power']:.1f}W<br>"
            f"电压: {room['voltage']:.0f}V<br>"
            f"烟雾: {room['smoke_density']:.3f}ppm<br>"
            f"状态: {status}"
        )
        hover_marker_colors.append(color)

    # 添加不可见的 hover 层
    fig.add_trace(go.Scatter(
        x=hover_x,
        y=hover_y,
        mode="markers",
        marker=dict(size=40, color="rgba(0,0,0,0)"),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_text,
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.1, n_cols]),
        yaxis=dict(visible=False, range=[-0.1, n_rows]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=180,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=COLOR_BG_CARD,
            bordercolor=COLOR_BORDER,
            font=dict(color=COLOR_TEXT_PRIMARY, size=12),
        ),
    )

    return fig


def build_architecture_diagram() -> go.Figure:
    """构建系统架构图

    Returns:
        Plotly Figure 对象，展示物联网三层架构
    """
    fig = go.Figure()

    # 定义三层架构
    layers = [
        {
            "name": "应用层",
            "y": 2,
            "color": COLOR_PRIMARY,
            "components": [
                {"name": "Streamlit 大屏", "x": 1},
                {"name": "AI Agent", "x": 3},
                {"name": "数据可视化", "x": 5},
            ],
        },
        {
            "name": "网络层",
            "y": 1,
            "color": COLOR_PRIMARY_LIGHT,
            "components": [
                {"name": "MQTT Broker", "x": 1},
                {"name": "Topic 路由", "x": 3},
                {"name": "消息队列", "x": 5},
            ],
        },
        {
            "name": "感知层",
            "y": 0,
            "color": COLOR_PRIMARY_HIGHLIGHT,
            "components": [
                {"name": "波形合成", "x": 1},
                {"name": "数据采集", "x": 3},
                {"name": "状态监测", "x": 5},
            ],
        },
    ]

    # 绘制每一层
    for layer in layers:
        y = layer["y"]

        # 层背景
        fig.add_shape(
            type="rect",
            x0=-0.5, y0=y - 0.4,
            x1=7, y1=y + 0.4,
            fillcolor=layer["color"],
            opacity=0.15,
            line=dict(color=layer["color"], width=1),
        )

        # 层名称
        fig.add_annotation(
            x=-0.2, y=y,
            text=f"<b>{layer['name']}</b>",
            showarrow=False,
            font=dict(size=14, color="white"),
            xanchor="center",
        )

        # 绘制组件
        for comp in layer["components"]:
            x = comp["x"]

            # 组件框
            fig.add_shape(
                type="rect",
                x0=x - 0.6, y0=y - 0.25,
                x1=x + 0.6, y1=y + 0.25,
                fillcolor=layer["color"],
                opacity=0.6,
                line=dict(color=layer["color"], width=1),
            )

            # 组件名称
            fig.add_annotation(
                x=x, y=y,
                text=comp["name"],
                showarrow=False,
                font=dict(size=10, color="white"),
            )

    # 绘制层间箭头（数据流向）
    # 感知层 → 网络层
    fig.add_annotation(
        x=3, y=0.5,
        ax=3, ay=0.7,
        xref="x", yref="y",
        axref="x", ayref="y",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.5,
        arrowcolor=COLOR_TEXT_SECONDARY,
    )
    fig.add_annotation(
        x=3, y=0.65,
        text="数据上报",
        showarrow=False,
        font=dict(size=8, color=COLOR_TEXT_SECONDARY),
    )

    # 网络层 → 应用层
    fig.add_annotation(
        x=3, y=1.5,
        ax=3, ay=1.7,
        xref="x", yref="y",
        axref="x", ayref="y",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.5,
        arrowcolor=COLOR_TEXT_SECONDARY,
    )
    fig.add_annotation(
        x=3, y=1.65,
        text="消息推送",
        showarrow=False,
        font=dict(size=8, color=COLOR_TEXT_SECONDARY),
    )

    # 应用层 → 网络层（控制指令）
    fig.add_annotation(
        x=5, y=1.7,
        ax=5, ay=1.5,
        xref="x", yref="y",
        axref="x", ayref="y",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.5,
        arrowcolor=COLOR_WARNING,
    )
    fig.add_annotation(
        x=5, y=1.65,
        text="控制指令",
        showarrow=False,
        font=dict(size=8, color=COLOR_WARNING),
    )

    fig.update_layout(
        title=dict(
            text="系统架构图（物联网三层架构）",
            font=dict(color=COLOR_TEXT_PRIMARY, size=14),
        ),
        xaxis=dict(visible=False, range=[-1, 7.5]),
        yaxis=dict(visible=False, range=[-0.6, 2.8]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
    )

    return fig


def build_building_overview(rooms_data: list[dict[str, Any]], floors: int, rooms_per_floor: int) -> go.Figure:
    """构建整栋楼概览图，支持 hover 交互

    Args:
        rooms_data: 所有房间数据
        floors: 楼层数
        rooms_per_floor: 每层房间数

    Returns:
        Plotly Figure 对象，展示整栋楼的状态
    """
    fig = go.Figure()

    # 按楼层分组
    floor_data = {}
    for room in rooms_data:
        floor = int(room["id"][0])
        if floor not in floor_data:
            floor_data[floor] = []
        floor_data[floor].append(room)

    # 收集 hover 数据
    hover_x = []
    hover_y = []
    hover_text = []

    # 绘制每层楼
    for floor in range(floors, 0, -1):
        y_offset = (floors - floor) * 1.2
        rooms = floor_data.get(floor, [])

        # 楼层标签
        fig.add_annotation(
            x=-1.5,
            y=y_offset + 0.45,
            text=f"<b>{floor}F</b>",
            showarrow=False,
            font=dict(size=12, color=COLOR_TEXT_PRIMARY),
            xanchor="center",
        )

        # 绘制房间
        for i, room in enumerate(rooms):
            x = i * 1.1
            color = room["color"]

            fig.add_shape(
                type="rect",
                x0=x, y0=y_offset, x1=x+1, y1=y_offset+0.9,
                fillcolor=color,
                opacity=0.6,
                line=dict(color=color, width=0.5),
            )

            # 房间号
            fig.add_annotation(
                x=x+0.5, y=y_offset+0.45,
                text=room["id"],
                showarrow=False,
                font=dict(size=8, color="white"),
            )

            # hover 数据
            hover_x.append(x + 0.5)
            hover_y.append(y_offset + 0.45)
            status = get_status_text(room["power"])
            hover_text.append(
                f"<b>Room {room['id']}</b><br>"
                f"功率: {room['power']:.1f}W<br>"
                f"电压: {room['voltage']:.0f}V<br>"
                f"状态: {status}"
            )

    # 添加不可见的 hover 层
    fig.add_trace(go.Scatter(
        x=hover_x,
        y=hover_y,
        mode="markers",
        marker=dict(size=30, color="rgba(0,0,0,0)"),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_text,
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="宿舍楼总览",
            font=dict(color=COLOR_TEXT_PRIMARY, size=14),
        ),
        xaxis=dict(visible=False, range=[-2, rooms_per_floor * 1.1 + 1]),
        yaxis=dict(visible=False, range=[-0.2, floors * 1.2]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=max(200, floors * 100),
        margin=dict(l=40, r=10, t=40, b=10),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=COLOR_BG_CARD,
            bordercolor=COLOR_BORDER,
            font=dict(color=COLOR_TEXT_PRIMARY, size=12),
        ),
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
