"""DormIoT-Twin — 宿舍安全监控数字孪生系统

政企科技大屏风格，绿色主色调。
集成：MQTT 仿真层 + 物理波形合成 + AI Agent 研判。
"""
from __future__ import annotations

import time
import streamlit as st

from dormiot.data_store import DataStore, BackgroundCollector
from dormiot.simulation.synthesizer import WaveformSynthesizer
from dormiot.ai_diagnoser import AIDiagnoser
from dormiot.protocol.mqtt_simulator import MQTTBroker
from dormiot.schemas.device import DeviceStatus
from dormiot.ui.helpers import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_PRIMARY_HIGHLIGHT,
    COLOR_ALARM,
    COLOR_WARNING,
    COLOR_SUCCESS,
    COLOR_BG_MAIN,
    COLOR_BG_CARD,
    COLOR_BG_SIDEBAR,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_NEON_GREEN,
    COLOR_NEON_RED,
    COLOR_CYAN,
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

# ═══════════════════════════════════════════════════════════
#  政企科技风 CSS（绿色主题）
# ═══════════════════════════════════════════════════════════

GOV_CSS = f"""
<style>
/* ── 全局 ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

.stApp {{
    background: linear-gradient(180deg, {COLOR_BG_MAIN} 0%, #081510 100%);
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
}}

/* ── 侧边栏 ── */
section[data-testid="stSidebar"] {{
    background: {COLOR_BG_SIDEBAR};
    border-right: 1px solid {COLOR_BORDER};
}}
section[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {COLOR_PRIMARY_LIGHT};
}}

/* ── 顶部状态栏 ── */
.top-status-bar {{
    background: linear-gradient(90deg, {COLOR_BG_CARD} 0%, {COLOR_BG_MAIN} 100%);
    border-bottom: 2px solid {COLOR_PRIMARY};
    border-radius: 0 0 12px 12px;
    padding: 16px 28px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.top-status-bar .system-name {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR_PRIMARY_LIGHT};
    letter-spacing: 1px;
}}
.top-status-bar .system-name .icon {{
    font-size: 26px;
    margin-right: 8px;
}}
.top-status-bar .stats {{
    display: flex;
    gap: 32px;
}}
.stat-item {{
    text-align: center;
}}
.stat-value {{
    font-size: 26px;
    font-weight: 600;
    color: {COLOR_PRIMARY};
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
}}
.stat-value.alarm {{
    color: {COLOR_ALARM};
}}
.stat-value.warning {{
    color: {COLOR_WARNING};
}}
.stat-label {{
    font-size: 11px;
    color: {COLOR_TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── 房间卡片 ── */
.room-card {{
    background: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}
.room-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: {COLOR_PRIMARY};
}}
.room-card:hover {{
    border-color: {COLOR_PRIMARY_LIGHT};
    box-shadow: 0 4px 20px rgba(44, 168, 106, 0.2);
    transform: translateY(-2px);
}}
.room-card.alarm {{
    border-color: {COLOR_ALARM};
}}
.room-card.alarm::before {{
    background: {COLOR_ALARM};
    animation: alarm-pulse 2s ease-in-out infinite;
}}
.room-card.warning::before {{
    background: {COLOR_WARNING};
}}
@keyframes alarm-pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
}}
.room-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}}
.room-id {{
    font-size: 15px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}
.room-status {{
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 500;
}}
.room-status.normal {{
    background: rgba(39, 174, 96, 0.15);
    color: {COLOR_SUCCESS};
}}
.room-status.warning {{
    background: rgba(243, 156, 18, 0.15);
    color: {COLOR_WARNING};
}}
.room-status.alarm {{
    background: rgba(231, 76, 60, 0.15);
    color: {COLOR_ALARM};
}}
.room-power {{
    font-size: 32px;
    font-weight: 700;
    color: {COLOR_PRIMARY};
    font-variant-numeric: tabular-nums;
    line-height: 1;
    margin: 8px 0;
}}
.room-power.alarm {{
    color: {COLOR_ALARM};
}}
.room-power.warning {{
    color: {COLOR_WARNING};
}}
.room-unit {{
    font-size: 14px;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 400;
}}
.room-meta {{
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid {COLOR_BORDER};
    font-size: 12px;
    color: {COLOR_TEXT_SECONDARY};
}}

/* ── AI Agent 工作台 ── */
.agent-panel {{
    background: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
}}
.agent-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid {COLOR_BORDER};
}}
.agent-header .icon {{
    font-size: 20px;
}}
.agent-header .title {{
    font-size: 16px;
    font-weight: 600;
    color: {COLOR_PRIMARY_LIGHT};
}}
.agent-header .status {{
    margin-left: auto;
    font-size: 12px;
    color: {COLOR_SUCCESS};
}}
.agent-section {{
    margin-bottom: 12px;
}}
.agent-section-title {{
    font-size: 12px;
    font-weight: 600;
    color: {COLOR_PRIMARY};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}}
.agent-item {{
    font-size: 13px;
    color: {COLOR_TEXT_SECONDARY};
    padding: 2px 0;
}}
.agent-item .label {{
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 500;
}}
.diagnosis-box {{
    background: rgba(35, 142, 84, 0.08);
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    line-height: 1.6;
}}
.diagnosis-box.error {{
    background: rgba(231, 76, 60, 0.08);
    border-color: {COLOR_ALARM};
}}

/* ── MQTT 日志 ── */
.mqtt-log {{
    background: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 16px;
    max-height: 200px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.8;
    color: {COLOR_TEXT_SECONDARY};
}}
.mqtt-log .alarm {{
    color: {COLOR_ALARM};
}}

/* ── 隐藏 Streamlit 默认元素 ── */
#MainMenu {{visibility: hidden;}}
header {{visibility: hidden;}}
footer {{visibility: hidden;}}
.block-container {{padding-top: 1rem; max-width: 100%;}}
</style>
"""

# ═══════════════════════════════════════════════════════════
#  页面配置
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="DormIoT-Twin 宿舍安全监控",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(GOV_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  全局初始化（单例 + 后台线程）
# ═══════════════════════════════════════════════════════════

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.start_time = time.time()
    st.session_state.alarm_log: list[dict] = []
    st.session_state.ai_call_cooldown: dict[str, float] = {}
    st.session_state.selected_room: str | None = None
    st.session_state.agent_diagnoses: list[dict] = []  # AI Agent 研判历史

store = DataStore()
synth = WaveformSynthesizer()
diagnoser = AIDiagnoser()
broker = MQTTBroker()

# 启动后台采集线程（如果尚未启动）
if "collector_started" not in st.session_state:
    st.session_state.collector_started = True
    collector = BackgroundCollector(interval_s=1.0)
    collector.start()


# ═══════════════════════════════════════════════════════════
#  AI 功率飙升检测与诊断
# ═══════════════════════════════════════════════════════════

def check_power_spikes() -> None:
    """检测功率飙升并触发 AI 诊断"""
    for room_id in ["101", "102", "103", "104", "105", "106"]:
        # 冷却检查（每房间 10 秒内不重复触发）
        last_call = st.session_state.ai_call_cooldown.get(room_id, 0)
        if time.time() - last_call < 10:
            continue

        if store.detect_power_spike(room_id):
            st.session_state.ai_call_cooldown[room_id] = time.time()

            power_array = store.get_power_array(room_id)
            waveform_type = diagnoser.classify_waveform(power_array)
            diagnosis = diagnoser.analyze_power_array(power_array, room_id)

            entry = build_alarm_log_entry(room_id, power_array, diagnosis)
            st.session_state.alarm_log.insert(0, entry)
            st.session_state.agent_diagnoses.insert(0, {
                "room_id": room_id,
                "waveform_type": waveform_type,
                "power_array": power_array[-10:],
                "diagnosis": diagnosis,
                "timestamp": time.strftime("%H:%M:%S"),
            })

    # 限制日志数量
    st.session_state.alarm_log = st.session_state.alarm_log[:20]
    st.session_state.agent_diagnoses = st.session_state.agent_diagnoses[:20]


check_power_spikes()


# ═══════════════════════════════════════════════════════════
#  侧边栏：控制面板
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙ 控制面板")

    st.markdown("---")
    st.markdown("#### ⚡ 异常注入")
    inject_room = st.selectbox("选择房间", ["101", "102", "103", "104", "105", "106"])
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔥 热得快", use_container_width=True):
            synth.set_alarm_mode(inject_room, DeviceStatus.ALARM_RESISTOR)
            st.toast(f"房间 {inject_room} 已注入热得快波形", icon="🔥")
    with col2:
        if st.button("📻 微波炉", use_container_width=True):
            synth.set_alarm_mode(inject_room, DeviceStatus.ALARM_MICROWAVE)
            st.toast(f"房间 {inject_room} 已注入微波炉波形", icon="📻")

    if st.button("✖ 清除当前异常", use_container_width=True):
        synth.clear_alarm_mode(inject_room)
        st.toast(f"房间 {inject_room} 已恢复正常", icon="✅")

    if st.button("🔄 重置所有房间", use_container_width=True):
        synth.reset()
        store.reset()
        st.session_state.alarm_log = []
        st.session_state.agent_diagnoses = []
        st.session_state.ai_call_cooldown = {}
        st.toast("所有房间已重置", icon="🔄")

    st.markdown("---")
    st.markdown("#### 🤖 AI Agent 演示")
    demo_room = st.selectbox("选择分析房间", ["101", "102", "103", "104", "105", "106"], key="demo_room")
    if st.button("🔬 触发 AI 研判", use_container_width=True):
        power_array = store.get_power_array(demo_room)
        if len(power_array) >= 3:
            waveform_type = diagnoser.classify_waveform(power_array)
            diagnosis = diagnoser.analyze_power_array(power_array, demo_room)
            st.session_state.agent_diagnoses.insert(0, {
                "room_id": demo_room,
                "waveform_type": waveform_type,
                "power_array": power_array[-10:],
                "diagnosis": diagnosis,
                "timestamp": time.strftime("%H:%M:%S"),
            })
            st.toast(f"AI 研判完成：{demo_room}", icon="🤖")
        else:
            st.warning("数据不足，请等待采集")

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center; color:{COLOR_TEXT_SECONDARY}; font-size:12px;'>"
        f"DormIoT-Twin v2.0<br>宿舍安全监控数字孪生系统"
        f"</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
#  顶部状态栏
# ═══════════════════════════════════════════════════════════

snapshot = store.latest_snapshot
rooms_data = build_room_grid_data(snapshot)

total_power = sum(r["power"] for r in rooms_data)
alarm_count = sum(1 for r in rooms_data if r["power"] > POWER_ALARM_THRESHOLD)
warning_count = sum(1 for r in rooms_data if POWER_WARNING_THRESHOLD < r["power"] <= POWER_ALARM_THRESHOLD)
runtime = time.time() - st.session_state.get("start_time", time.time())
runtime_str = time.strftime("%H:%M:%S", time.gmtime(runtime))

st.markdown(
    f"""
    <div class="top-status-bar">
        <div class="system-name">
            <span class="icon">🏠</span>
            DormIoT-Twin 宿舍安全监控数字孪生
        </div>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{total_power:.0f}W</div>
                <div class="stat-label">实时总功率</div>
            </div>
            <div class="stat-item">
                <div class="stat-value{' alarm' if alarm_count > 0 else ''}">{alarm_count}</div>
                <div class="stat-label">告警房间</div>
            </div>
            <div class="stat-item">
                <div class="stat-value{' warning' if warning_count > 0 else ''}">{warning_count}</div>
                <div class="stat-label">预警房间</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{runtime_str}</div>
                <div class="stat-label">运行时长</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
#  主体区域：左侧 AI Agent + 右侧房间网格
# ═══════════════════════════════════════════════════════════

col_agent, col_rooms = st.columns([2, 5])

# ── 左侧：AI Agent 工作台 ──
with col_agent:
    st.markdown(
        f"""
        <div class="agent-panel">
            <div class="agent-header">
                <span class="icon">🤖</span>
                <span class="title">AI 安全专家 Agent</span>
                <span class="status">● 运行中</span>
            </div>
            <div class="agent-section">
                <div class="agent-section-title">【感知层】</div>
                <div class="agent-item">监控房间: 101-106 (6间)</div>
                <div class="agent-item">采样频率: 1Hz</div>
                <div class="agent-item">当前总功率: <span class="label">{total_power:.0f}W</span></div>
                <div class="agent-item">异常检测: {POWER_ALARM_THRESHOLD:.0f}W 阈值</div>
            </div>
            <div class="agent-section">
                <div class="agent-section-title">【推理层】</div>
                <div class="agent-item">波形分类器: 统计特征分析</div>
                <div class="agent-item">LLM 分析: OpenAI 兼容 API</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 最新研判结果
    if st.session_state.agent_diagnoses:
        latest = st.session_state.agent_diagnoses[0]
        power_str = ", ".join(f"{p:.0f}" for p in latest["power_array"][-6:])
        st.markdown(
            f"""
            <div class="agent-panel">
                <div class="agent-section-title">【最新研判】</div>
                <div class="agent-item">时间: {latest['timestamp']}</div>
                <div class="agent-item">房间: <span class="label">{latest['room_id']}</span></div>
                <div class="agent-item">波形: <span class="label">{latest['waveform_type']}</span></div>
                <div class="agent-item">数据: [{power_str}]</div>
                <div class="diagnosis-box">{latest['diagnosis']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="agent-panel">
                <div class="agent-section-title">【最新研判】</div>
                <div class="agent-item" style="color:{COLOR_TEXT_SECONDARY};">
                    暂无研判 — 等待异常触发或手动演示
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 历史研判（最近 5 条）
    if len(st.session_state.agent_diagnoses) > 1:
        with st.expander(f"📜 历史研判 ({len(st.session_state.agent_diagnoses)} 条)", expanded=False):
            for diag in st.session_state.agent_diagnoses[1:6]:
                st.markdown(
                    f"<span style='color:{COLOR_TEXT_SECONDARY}; font-size:12px;'>"
                    f"{diag['timestamp']} · Room {diag['room_id']} · {diag['waveform_type']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:13px; margin-bottom:8px; color:{COLOR_TEXT_PRIMARY};'>"
                    f"{diag['diagnosis']}</div>",
                    unsafe_allow_html=True,
                )

# ── 右侧：房间网格（2×3）──
with col_rooms:
    for row in range(2):
        cols = st.columns(3)
        for col_idx in range(3):
            room = rooms_data[row * 3 + col_idx]
            with cols[col_idx]:
                power = room["power"]
                status_class = "alarm" if power > POWER_ALARM_THRESHOLD else ("warning" if power > POWER_WARNING_THRESHOLD else "normal")
                power_class = "alarm" if power > POWER_ALARM_THRESHOLD else ("warning" if power > POWER_WARNING_THRESHOLD else "")

                sparkline_html = ""
                room_history = store.get_power_array(room["id"])
                if len(room_history) > 1:
                    recent = room_history[-20:]
                    max_p = max(recent) if recent else 1
                    min_p = min(recent) if recent else 0
                    p_range = max_p - min_p if max_p != min_p else 1
                    points = " ".join(
                        f"{i * (160 / max(len(recent) - 1, 1))},{40 - int((p - min_p) / p_range * 35)}"
                        for i, p in enumerate(recent)
                    )
                    sparkline_color = get_room_color(power)
                    sparkline_html = f"""
                    <svg width="160" height="42" style="margin-top:4px;">
                        <polyline points="{points}"
                            fill="none" stroke="{sparkline_color}" stroke-width="1.5"
                            stroke-linejoin="round" stroke-linecap="round"/>
                    </svg>
                    """

                st.markdown(
                    f"""
                    <div class="room-card {status_class}">
                        <div class="room-header">
                            <span class="room-id">ROOM {room['id']}</span>
                            <span class="room-status {status_class}">{room['status_text']}</span>
                        </div>
                        <div class="room-power {power_class}">
                            {power:.1f} <span class="room-unit">W</span>
                        </div>
                        {sparkline_html}
                        <div class="room-meta">
                            <span>{room['voltage']:.0f}V</span>
                            <span>烟雾: {room['smoke_density']:.3f}ppm</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── 房间选择器（用于波形图）──
    selected_room = st.selectbox(
        "选择房间查看详细波形",
        ["101", "102", "103", "104", "105", "106"],
        key="chart_room",
    )


# ═══════════════════════════════════════════════════════════
#  底部：实时波形图 + MQTT 通信日志
# ═══════════════════════════════════════════════════════════

st.markdown("---")

col_chart, col_mqtt = st.columns([3, 2])

# ── 波形图 ──
with col_chart:
    chart_room = st.session_state.get("chart_room", "101")
    room_history = store.get_room_history(chart_room)

    if room_history:
        timestamps = [
            time.strftime("%H:%M:%S", time.localtime(time.time() - len(room_history) + i))
            for i in range(len(room_history))
        ]
        values = [d["power"] for d in room_history]
        fig = build_power_chart(timestamps, values, room_id=chart_room)
        st.plotly_chart(fig, use_container_width=True, key="power_chart")
    else:
        st.info(f"房间 {chart_room} 暂无数据，请等待采集...")

# ── MQTT 通信日志 ──
with col_mqtt:
    st.markdown(f"##### 📡 MQTT 通信日志")
    mqtt_msgs = broker.get_recent_messages(limit=15)
    if mqtt_msgs:
        log_html = '<div class="mqtt-log">'
        for msg in reversed(mqtt_msgs):
            topic = msg["topic"]
            payload = msg["payload"]
            power = payload.get("power", 0)
            alarm_cls = "alarm" if power > POWER_ALARM_THRESHOLD else ""
            icon = "⚠" if power > POWER_ALARM_THRESHOLD else "→"
            log_html += f'<div class="{alarm_cls}">{icon} {topic} | {power:.1f}W</div>'
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="mqtt-log" style="color:{COLOR_TEXT_SECONDARY};">等待 MQTT 消息...</div>',
            unsafe_allow_html=True,
        )

    # 告警日志
    if st.session_state.alarm_log:
        st.markdown(f"##### 🚨 AI 告警日志")
        for entry in st.session_state.alarm_log[:5]:
            st.markdown(
                f"""
                <div style="background:{COLOR_BG_CARD}; border-left:3px solid {COLOR_ALARM};
                            border-radius:0 8px 8px 0; padding:10px 14px; margin:6px 0;
                            font-size:13px;">
                    <span style="color:{COLOR_ALARM}; font-weight:600;">
                        ⚠ 房间 {entry['room_id']}</span>
                    <span style="color:{COLOR_TEXT_SECONDARY}; margin-left:8px;">
                        {entry['timestamp']} · {entry['power']:.0f}W</span>
                    <div style="color:{COLOR_TEXT_PRIMARY}; margin-top:4px;">
                        {entry.get('diagnosis', '研判中...')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════
#  自动刷新（每秒重绘）
# ═══════════════════════════════════════════════════════════

time.sleep(1)
st.rerun()
