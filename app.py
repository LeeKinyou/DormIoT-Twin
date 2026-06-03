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
    COLOR_ALARM,
    COLOR_WARNING,
    COLOR_SUCCESS,
    COLOR_BG_MAIN,
    COLOR_BG_CARD,
    COLOR_BG_SIDEBAR,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    POWER_ALARM_THRESHOLD,
    POWER_WARNING_THRESHOLD,
    get_room_color,
    get_status_text,
    build_room_grid_data,
    build_power_chart,
    build_alarm_log_entry,
)

# ═══════════════════════════════════════════════════════════
#  页面配置（必须在所有 st 调用之前）
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="DormIoT-Twin 宿舍安全监控",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════

st.markdown(f"""
<style>
.stApp {{
    background: linear-gradient(180deg, {COLOR_BG_MAIN} 0%, #081510 100%);
    color: {COLOR_TEXT_PRIMARY};
}}
section[data-testid="stSidebar"] {{
    background: {COLOR_BG_SIDEBAR};
    border-right: 1px solid {COLOR_BORDER};
}}
#MainMenu {{visibility: hidden;}}
header {{visibility: hidden;}}
footer {{visibility: hidden;}}
.block-container {{padding-top: 0.5rem; max-width: 100%;}}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  全局初始化（单例 + 后台线程）
# ═══════════════════════════════════════════════════════════

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.start_time = time.time()
    st.session_state.alarm_log: list[dict] = []
    st.session_state.ai_call_cooldown: dict[str, float] = {}
    st.session_state.agent_diagnoses: list[dict] = []

store = DataStore()
synth = WaveformSynthesizer()
diagnoser = AIDiagnoser()
broker = MQTTBroker()

if "collector_started" not in st.session_state:
    st.session_state.collector_started = True
    collector = BackgroundCollector(interval_s=1.0)
    collector.start()


# ═══════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════

def check_power_spikes() -> None:
    """检测功率飙升并触发 AI 诊断"""
    for room_id in ["101", "102", "103", "104", "105", "106"]:
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
    st.session_state.alarm_log = st.session_state.alarm_log[:20]
    st.session_state.agent_diagnoses = st.session_state.agent_diagnoses[:20]


def trigger_ai_diagnosis(room_id: str) -> None:
    """手动触发 AI 研判"""
    power_array = store.get_power_array(room_id)
    if len(power_array) < 3:
        return
    waveform_type = diagnoser.classify_waveform(power_array)
    diagnosis = diagnoser.analyze_power_array(power_array, room_id)
    st.session_state.agent_diagnoses.insert(0, {
        "room_id": room_id,
        "waveform_type": waveform_type,
        "power_array": power_array[-10:],
        "diagnosis": diagnosis,
        "timestamp": time.strftime("%H:%M:%S"),
    })
    st.session_state.agent_diagnoses = st.session_state.agent_diagnoses[:20]


def render_room_card(room: dict, room_history: list) -> None:
    """用纯 Streamlit 组件渲染房间卡片（不依赖 HTML）"""
    power = room["power"]
    status_text = get_status_text(power)

    # 状态颜色
    if power > POWER_ALARM_THRESHOLD:
        border_color = COLOR_ALARM
    elif power > POWER_WARNING_THRESHOLD:
        border_color = COLOR_WARNING
    else:
        border_color = COLOR_PRIMARY

    # 用容器 + markdown 构建卡片
    with st.container(border=True):
        # 标题行
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**ROOM {room['id']}**")
        with c2:
            st.markdown(f"<span style='color:{border_color}; font-size:12px;'>{status_text}</span>",
                        unsafe_allow_html=True)

        # 功率数字
        st.markdown(
            f"<span style='font-size:28px; font-weight:700; color:{border_color}; "
            f"font-variant-numeric:tabular-nums;'>{power:.1f}</span>"
            f"<span style='font-size:13px; color:{COLOR_TEXT_SECONDARY};'> W</span>",
            unsafe_allow_html=True,
        )

        # 迷你趋势线（用 plotly 很小的图）
        if len(room_history) > 1:
            recent = room_history[-20:]
            mini_fig = {
                "data": [{"y": recent, "type": "scatter", "mode": "lines",
                          "line": {"color": border_color, "width": 1.5},
                          "fill": "tozeroy",
                          "fillcolor": f"rgba(35, 142, 84, 0.1)"}],
                "layout": {
                    "height": 40, "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
                    "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
                    "xaxis": {"visible": False}, "yaxis": {"visible": False},
                    "showlegend": False,
                },
            }
            st.plotly_chart(mini_fig, use_container_width=True, key=f"spark_{room['id']}")

        # 底部元数据
        st.caption(f"{room['voltage']:.0f}V · 烟雾: {room['smoke_density']:.3f}ppm")


check_power_spikes()

# ═══════════════════════════════════════════════════════════
#  主页面 Tabs
# ═══════════════════════════════════════════════════════════

tab_monitor, tab_config = st.tabs(["📊 实时监控", "⚙ 配置中心"])


# ═══════════════════════════════════════════════════════════
#  Tab 1: 实时监控（用 @st.fragment 局部刷新）
# ═══════════════════════════════════════════════════════════

with tab_monitor:
    # ── 顶部状态栏 ──
    @st.fragment(run_every="1s")
    def status_bar():
        snapshot = store.latest_snapshot
        rooms_data = build_room_grid_data(snapshot)
        total_power = sum(r["power"] for r in rooms_data)
        alarm_count = sum(1 for r in rooms_data if r["power"] > POWER_ALARM_THRESHOLD)
        warning_count = sum(1 for r in rooms_data if POWER_WARNING_THRESHOLD < r["power"] <= POWER_ALARM_THRESHOLD)
        runtime = time.time() - st.session_state.get("start_time", time.time())
        runtime_str = time.strftime("%H:%M:%S", time.gmtime(runtime))

        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        with c1:
            st.markdown(f"### 🏠 DormIoT-Twin")
        with c2:
            st.metric("总功率", f"{total_power:.0f}W")
        with c3:
            st.metric("告警", f"{alarm_count}", delta=f"-{alarm_count}" if alarm_count else None)
        with c4:
            st.metric("预警", f"{warning_count}")
        with c5:
            st.metric("运行", runtime_str)

    status_bar()

    # ── 主体：左侧 Agent + 右侧房间 ──
    col_agent, col_rooms = st.columns([2, 5])

    # 左侧：AI Agent（静态，不自动刷新）
    with col_agent:
        st.markdown("#### 🤖 AI 安全专家 Agent")
        st.caption("感知层: 6 间宿舍 · 1Hz 采样 · 60s 历史")
        st.caption("推理层: 波形分类 → LLM 研判")

        if st.session_state.agent_diagnoses:
            latest = st.session_state.agent_diagnoses[0]
            power_str = ", ".join(f"{p:.0f}" for p in latest["power_array"][-6:])
            st.markdown(f"**最新研判** `{latest['timestamp']}`")
            st.markdown(f"Room **{latest['room_id']}** · `{latest['waveform_type']}`")
            st.code(f"[{power_str}]", language=None)
            st.info(latest["diagnosis"])
        else:
            st.caption("暂无研判 — 使用「配置中心」触发异常或手动分析")

        if len(st.session_state.agent_diagnoses) > 1:
            with st.expander(f"📜 历史研判 ({len(st.session_state.agent_diagnoses)} 条)"):
                for diag in st.session_state.agent_diagnoses[1:6]:
                    st.caption(f"`{diag['timestamp']}` · Room {diag['room_id']} · {diag['waveform_type']}")
                    st.markdown(diag["diagnosis"])

    # 右侧：房间网格（局部刷新）
    with col_rooms:
        @st.fragment(run_every="1s")
        def room_grid():
            snapshot = store.latest_snapshot
            rooms_data = build_room_grid_data(snapshot)

            for row in range(2):
                cols = st.columns(3)
                for col_idx in range(3):
                    room = rooms_data[row * 3 + col_idx]
                    with cols[col_idx]:
                        history = store.get_power_array(room["id"])
                        render_room_card(room, history)

        room_grid()

        selected_room = st.selectbox(
            "选择房间查看详细波形",
            ["101", "102", "103", "104", "105", "106"],
            key="chart_room",
        )

    # ── 底部：波形图 + MQTT 日志（局部刷新）──
    st.markdown("---")

    @st.fragment(run_every="1s")
    def bottom_panel():
        col_chart, col_mqtt = st.columns([3, 2])

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
                st.info(f"房间 {chart_room} 暂无数据...")

        with col_mqtt:
            st.markdown("**📡 MQTT 通信日志**")
            mqtt_msgs = broker.get_recent_messages(limit=10)
            if mqtt_msgs:
                for msg in reversed(mqtt_msgs):
                    power = msg["payload"].get("power", 0)
                    topic = msg["topic"]
                    if power > POWER_ALARM_THRESHOLD:
                        st.markdown(f":red[⚠ `{topic.split('/')[-2]}` **{power:.1f}W**]")
                    else:
                        st.caption(f"→ `{topic.split('/')[-2]}` {power:.1f}W")

            if st.session_state.alarm_log:
                st.markdown("**🚨 AI 告警**")
                for entry in st.session_state.alarm_log[:3]:
                    st.markdown(f":red[⚠ Room {entry['room_id']}] {entry['power']:.0f}W")
                    st.caption(entry.get("diagnosis", ""))

    bottom_panel()


# ═══════════════════════════════════════════════════════════
#  Tab 2: 配置中心
# ═══════════════════════════════════════════════════════════

with tab_config:
    st.markdown("### ⚙ 配置中心")

    col_inject, col_ai = st.columns(2)

    # ── 异常注入 ──
    with col_inject:
        st.markdown("#### ⚡ 异常注入")
        inject_room = st.selectbox("选择房间", ["101", "102", "103", "104", "105", "106"], key="inject_room")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔥 热得快", use_container_width=True):
                synth.set_alarm_mode(inject_room, DeviceStatus.ALARM_RESISTOR)
                st.toast(f"房间 {inject_room} 已注入热得快波形", icon="🔥")
        with c2:
            if st.button("📻 微波炉", use_container_width=True):
                synth.set_alarm_mode(inject_room, DeviceStatus.ALARM_MICROWAVE)
                st.toast(f"房间 {inject_room} 已注入微波炉波形", icon="📻")
        with c3:
            if st.button("✖ 清除异常", use_container_width=True):
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
        st.markdown("#### 📋 当前房间状态")
        current = store.latest_snapshot
        for rid in ["101", "102", "103", "104", "105", "106"]:
            d = current.get(rid, {})
            p = d.get("power", 0)
            mode = synth._alarm_modes.get(rid, DeviceStatus.NORMAL)
            mode_str = mode.value if hasattr(mode, "value") else str(mode)
            color = "red" if p > POWER_ALARM_THRESHOLD else ("orange" if p > POWER_WARNING_THRESHOLD else "green")
            st.markdown(f":{color}[**{rid}**] {p:.1f}W · `{mode_str}`")

    # ── AI 手动研判 ──
    with col_ai:
        st.markdown("#### 🤖 AI Agent 手动研判")
        st.markdown("选择房间 → 查看当前波形数据 → 点击触发 AI 分析")

        ai_room = st.selectbox("选择房间", ["101", "102", "103", "104", "105", "106"], key="ai_room")

        power_array = store.get_power_array(ai_room)
        if power_array:
            st.markdown(f"**当前数据**（{len(power_array)} 个采样点）：")
            st.code(f"[{', '.join(f'{p:.1f}' for p in power_array[-10:])}]")
            waveform_type = diagnoser.classify_waveform(power_array)
            st.markdown(f"**波形分类**: `{waveform_type}`")
        else:
            st.warning("暂无数据，等待采集线程...")

        if st.button("🔬 触发 AI 研判", use_container_width=True, type="primary"):
            if len(power_array) >= 3:
                with st.spinner("AI 分析中..."):
                    trigger_ai_diagnosis(ai_room)
                st.toast(f"研判完成: {ai_room}", icon="🤖")
                st.rerun()
            else:
                st.error("数据不足（至少 3 个采样点）")

        if st.session_state.agent_diagnoses:
            st.markdown("---")
            st.markdown("#### 📜 研判结果")
            for i, diag in enumerate(st.session_state.agent_diagnoses[:5]):
                power_str = ", ".join(f"{p:.0f}" for p in diag["power_array"][-6:])
                with st.expander(
                    f"`{diag['timestamp']}` · Room {diag['room_id']} · {diag['waveform_type']}",
                    expanded=(i == 0),
                ):
                    st.code(f"[{power_str}]")
                    st.markdown(diag["diagnosis"])
