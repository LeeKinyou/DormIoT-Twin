"""DormIoT-Twin — 宿舍物联网安全监控数字孪生系统

启动方式：uv run streamlit run app.py
"""
from __future__ import annotations

import time

import streamlit as st

from dormiot.ai_diagnoser import AIDiagnoser
from dormiot.data_store import BackgroundCollector, DataStore
from dormiot.schemas.device import DeviceStatus
from dormiot.simulation.synthesizer import WaveformSynthesizer
from dormiot.ui.helpers import (
    ALERT_LOG_KEY,
    COLOR_DARK_BG,
    COLOR_NEON_GREEN,
    COLOR_NEON_RED,
    COLOR_PANEL_BG,
    COLOR_TEXT,
    COLOR_CYAN,
    build_alarm_log_entry,
    build_power_chart,
    build_room_grid_data,
)

# ── 赛博朋克暗色主题 CSS ──
CYBERPUNK_CSS = """
<style>
    /* 全局暗色背景 */
    .stApp {
        background-color: #0a0a0f;
        color: #e0e0e0;
    }
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #0d0d14;
    }
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 房间卡片 */
    .room-card {
        background: #111118;
        border: 1px solid #1a1a2e;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .room-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }
    .room-card.normal::before {
        background: #00ff41;
        box-shadow: 0 0 10px #00ff41;
    }
    .room-card.alarm::before {
        background: #ff073a;
        box-shadow: 0 0 10px #ff073a;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .room-id {
        font-size: 24px;
        font-weight: bold;
        font-family: 'Courier New', monospace;
    }
    .room-power {
        font-size: 32px;
        font-weight: bold;
        font-family: 'Courier New', monospace;
    }
    .room-status {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* 告警日志 */
    .alert-entry {
        background: #111118;
        border-left: 3px solid #ff073a;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 0 4px 4px 0;
        font-family: 'Courier New', monospace;
        font-size: 13px;
    }
    .alert-entry .time {
        color: #666;
        font-size: 11px;
    }
    .alert-entry .room {
        color: #00d4ff;
        font-weight: bold;
    }
    .alert-entry .diag {
        color: #e0e0e0;
    }
</style>
"""


def init_session():
    """初始化 session state"""
    if "initialized" not in st.session_state:
        # 重置单例
        synth = WaveformSynthesizer()
        synth.reset()
        store = DataStore()
        store.reset()

        # 启动后台采集
        collector = BackgroundCollector(interval_s=1.0)
        collector.start()

        st.session_state.collector = collector
        st.session_state[ALERT_LOG_KEY] = []
        st.session_state.last_ai_call = {}
        st.session_state.initialized = True


def check_power_spikes():
    """检测功率飙升并触发 AI 诊断"""
    store = DataStore()
    diagnoser = AIDiagnoser()
    logs = st.session_state.get(ALERT_LOG_KEY, [])
    last_call = st.session_state.get("last_ai_call", {})

    for room_id in ["101", "102", "103", "104", "105", "106"]:
        if store.detect_power_spike(room_id, threshold=1000, window=2):
            now = time.time()
            if room_id in last_call and (now - last_call[room_id]) < 10:
                continue

            power_array = store.get_power_array(room_id)
            if len(power_array) >= 3:
                diagnosis = diagnoser.analyze_power_array(power_array, room_id)
                entry = build_alarm_log_entry(room_id, power_array, diagnosis)
                logs.append(entry)
                st.session_state[ALERT_LOG_KEY] = logs
                last_call[room_id] = now
                st.session_state.last_ai_call = last_call


def render_cyber_header():
    """渲染赛博朋克风格标题"""
    st.markdown(
        """
        <div style="text-align:center; padding: 10px 0;">
            <h1 style="
                font-family: 'Courier New', monospace;
                color: #00d4ff;
                text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
                margin: 0;
                font-size: 28px;
            ">
                ⚡ DormIoT-Twin ⚡ 宿舍安全监控数字孪生
            </h1>
            <p style="color: #666; font-size: 12px; margin: 4px 0;">
                REAL-TIME POWER MONITORING SYSTEM v2.0
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_alert_logs():
    """渲染告警日志卡片（顶部）"""
    logs = st.session_state.get(ALERT_LOG_KEY, [])
    if not logs:
        return

    st.markdown("##### 🚨 AI 安全研判日志")
    for entry in reversed(logs[-5:]):
        st.markdown(
            f"""
            <div class="alert-entry">
                <span class="time">[{entry['timestamp']}]</span>
                <span class="room"> Room {entry['room_id']}</span>
                &nbsp;⚡ {entry['current_power']:.0f}W &nbsp;│&nbsp;
                <span class="diag">{entry['ai_diagnosis']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_room_grid():
    """渲染 2.5D 空间拓扑 — 6 宫格"""
    store = DataStore()
    snapshot = store.latest_snapshot
    grid_data = build_room_grid_data(snapshot)

    st.markdown("##### 🏠 宿舍空间拓扑")
    cols = st.columns(3)
    for idx, room in enumerate(grid_data):
        col = cols[idx % 3]
        with col:
            card_class = "alarm" if room["color"] == COLOR_NEON_RED else "normal"
            status_label = {
                "NORMAL": "● 正常",
                "ALARM_RESISTOR": "⚡ 热得快",
                "ALARM_MICROWAVE": "🔲 微波炉",
                "WARNING": "⚠ 预警",
                "ALARM": "🚨 告警",
            }.get(room["status"], room["status"])

            power_color = room["color"]
            st.markdown(
                f"""
                <div class="room-card {card_class}">
                    <div class="room-id" style="color: {COLOR_CYAN};">ROOM {room['room_id']}</div>
                    <div class="room-power" style="color: {power_color};">{room['power']:.0f}W</div>
                    <div class="room-status" style="color: {COLOR_TEXT};">{status_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_power_charts():
    """渲染动态波形图（全房间 + 选中房间）"""
    store = DataStore()

    st.markdown("##### 📈 实时功率波形")

    # 全校总功率
    all_powers = []
    timestamps = []
    for i in range(store.history_length):
        total = 0.0
        for room_id in ["101", "102", "103", "104", "105", "106"]:
            hist = store.get_room_history(room_id)
            if i < len(hist):
                total += hist[i].get("power", 0.0)
        all_powers.append(round(total, 1))
        timestamps.append(f"T-{store.history_length - i}")

    fig = build_power_chart(timestamps, all_powers, room_id="全校总功率")
    st.plotly_chart(fig, use_container_width=True, key="power_trend_all")

    # 单房间功率
    selected_room = st.selectbox("选择房间查看详细波形", ["101", "102", "103", "104", "105", "106"])
    if selected_room:
        room_powers = store.get_power_array(selected_room)
        room_ts = [f"T-{len(room_powers) - i}" for i in range(len(room_powers))]
        room_fig = build_power_chart(room_ts, room_powers, room_id=selected_room)
        st.plotly_chart(room_fig, use_container_width=True, key=f"power_trend_{selected_room}")


def render_sidebar():
    """渲染侧边栏控制面板"""
    synth = WaveformSynthesizer()

    with st.sidebar:
        st.markdown("## 🎛️ 控制面板")
        st.markdown("---")

        # 异常注入
        st.markdown("### 💉 异常注入")
        target_room = st.selectbox("目标房间", ["101", "102", "103", "104", "105", "106"])
        inject_type = st.radio("异常类型", ["热得快 (1800W)", "微波炉 (方波)"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ 注入", use_container_width=True):
                mode = (
                    DeviceStatus.ALARM_RESISTOR
                    if "热得快" in inject_type
                    else DeviceStatus.ALARM_MICROWAVE
                )
                synth.set_alarm_mode(target_room, mode)
                st.success(f"已向 {target_room} 注入 {inject_type}")

        with col2:
            if st.button("🔄 清除", use_container_width=True):
                synth.clear_alarm_mode(target_room)
                st.info(f"已清除 {target_room} 异常")

        if st.button("🔄 重置全部", use_container_width=True):
            synth.reset()
            store = DataStore()
            store.reset()
            st.session_state[ALERT_LOG_KEY] = []
            st.success("已重置所有房间")

        st.markdown("---")

        # 系统状态
        st.markdown("### 📊 系统状态")
        store = DataStore()
        snapshot = store.latest_snapshot
        total_power = sum(d.get("power", 0) for d in snapshot.values())
        alarm_count = sum(
            1 for d in snapshot.values()
            if d.get("status", "NORMAL") != "NORMAL"
        )

        st.metric("总功率", f"{total_power:.0f} W")
        st.metric("异常房间", f"{alarm_count} / 6")
        st.metric("数据帧数", store.history_length)

        st.markdown("---")
        st.caption("DormIoT-Twin v2.0 | TDD 重构版")


def main():
    """主应用入口"""
    st.markdown(CYBERPUNK_CSS, unsafe_allow_html=True)
    init_session()
    check_power_spikes()

    render_sidebar()
    render_cyber_header()
    render_alert_logs()
    render_room_grid()
    render_power_charts()

    time.sleep(1)
    st.rerun()


if __name__ == "__main__":
    main()
