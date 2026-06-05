"""DormIoT-Twin — 宿舍安全监控数字孪生系统

政企科技大屏风格，绿色主色调。
集成：MQTT 仿真层 + 物理波形合成 + AI Agent 研判。
"""
from __future__ import annotations

import time
import streamlit as st

from dormiot.config import settings
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
    POWER_ALARM_THRESHOLD,
    POWER_WARNING_THRESHOLD,
    get_room_color,
    get_status_text,
    get_trend_info,
    build_room_grid_data,
    build_power_chart,
    build_floor_plan_chart,
    build_building_overview,
    build_architecture_diagram,
    build_ai_reasoning_chart,
    build_history_trend_chart,
    build_energy_statistics_chart,
    extract_waveform_features,
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

/* 告警闪烁动画 */
@keyframes alarm_pulse {{
    0% {{ opacity: 1; box-shadow: 0 0 15px rgba(231, 76, 60, 0.6); }}
    50% {{ opacity: 0.7; box-shadow: 0 0 30px rgba(231, 76, 60, 0.9); }}
    100% {{ opacity: 1; box-shadow: 0 0 15px rgba(231, 76, 60, 0.6); }}
}}

.alarm-active {{
    animation: alarm_pulse 1s infinite;
    border: 2px solid {COLOR_ALARM} !important;
    background: rgba(231, 76, 60, 0.15) !important;
}}

/* 预警呼吸效果 */
@keyframes warning_breathe {{
    0% {{ box-shadow: 0 0 5px rgba(243, 156, 18, 0.3); }}
    50% {{ box-shadow: 0 0 20px rgba(243, 156, 18, 0.7); }}
    100% {{ box-shadow: 0 0 5px rgba(243, 156, 18, 0.3); }}
}}

.warning-active {{
    animation: warning_breathe 2s infinite;
    border: 2px solid {COLOR_WARNING} !important;
    background: rgba(243, 156, 18, 0.1) !important;
}}

/* 正常状态 */
.normal-state {{
    border: 1px solid {COLOR_BORDER};
    background: {COLOR_BG_CARD};
}}

/* 告警横幅 */
.alarm-banner {{
    background: linear-gradient(90deg, rgba(231, 76, 60, 0.3), rgba(231, 76, 60, 0.1));
    border: 1px solid {COLOR_ALARM};
    border-radius: 8px;
    padding: 12px 20px;
    margin-bottom: 12px;
    animation: alarm_pulse 1.5s infinite;
}}

/* 预警横幅 */
.warning-banner {{
    background: linear-gradient(90deg, rgba(243, 156, 18, 0.2), rgba(243, 156, 18, 0.05));
    border: 1px solid {COLOR_WARNING};
    border-radius: 8px;
    padding: 12px 20px;
    margin-bottom: 12px;
    animation: warning_breathe 2s infinite;
}}

/* 告警声音提示（通过 JavaScript） */
.alarm-sound {{
    display: none;
}}
</style>

<script>
// Simple alarm sound
function playAlarm() {{
    try {{
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 800;
        gain.gain.value = 0.3;
        osc.start();
        osc.stop(ctx.currentTime + 0.5);
    }} catch(e) {{}}
}}

// Check for alarms every 2 seconds
setInterval(function() {{
    var alarms = document.querySelectorAll('.alarm-active');
    if (alarms.length > 0) {{
        playAlarm();
    }}
}}, 2000);
</script>
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
    st.session_state.demo_running = False
    st.session_state.demo_step = ""
    st.session_state.demo_progress = 0

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
    for room_id in synth.ROOMS:
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


def run_auto_demo() -> None:
    """一键自动演示：正常→注入热得快→检测→AI研判→恢复"""
    import time as _time

    steps = [
        ("▶ 正常运行中...", 0.1),
        ("🔥 注入热得快异常...", 0.2),
        ("⚡ 等待功率飙升检测...", 0.4),
        ("🤖 触发 AI 研判...", 0.6),
        ("📋 展示研判结果...", 0.8),
        ("✅ 清除异常，恢复正常...", 1.0),
    ]

    st.session_state.demo_running = True
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Step 1: 正常运行
    status_text.info(steps[0][0])
    progress_bar.progress(steps[0][1])
    _time.sleep(2)

    # Step 2: 注入热得快
    status_text.warning(steps[1][0])
    progress_bar.progress(steps[1][1])
    synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
    _time.sleep(3)

    # Step 3: 等待检测
    status_text.error(steps[2][0])
    progress_bar.progress(steps[2][1])
    _time.sleep(3)

    # Step 4: AI 研判
    status_text.info(steps[3][0])
    progress_bar.progress(steps[3][1])
    trigger_ai_diagnosis("101")
    _time.sleep(2)

    # Step 5: 展示结果
    status_text.success(steps[4][0])
    progress_bar.progress(steps[4][1])
    _time.sleep(3)

    # Step 6: 清除异常
    status_text.info(steps[5][0])
    progress_bar.progress(steps[5][1])
    synth.clear_alarm_mode("101")
    _time.sleep(2)

    # 完成
    status_text.success("✅ 演示完成！系统已恢复正常运行")
    progress_bar.progress(1.0)
    st.session_state.demo_running = False
    _time.sleep(2)
    status_text.empty()
    progress_bar.empty()
    st.rerun()


# ═══════════════════════════════════════════════════════════
#  侧边栏：演示模式 + 系统状态
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    # ── 实时时钟 ──
    @st.fragment(run_every="1s")
    def sidebar_clock():
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(
            f"<div style='text-align:center; font-size:12px; color:{COLOR_TEXT_SECONDARY};'>"
            f"🕐 {now}</div>",
            unsafe_allow_html=True,
        )
    sidebar_clock()

    st.markdown("---")
    st.markdown("### 🎬 演示模式")
    st.caption("一键展示完整安防流程")

    # 一键自动演示
    if st.button("▶ 一键自动演示", use_container_width=True, type="primary"):
        run_auto_demo()

    st.caption("或手动分步操作：")

    if st.button("🔥 注入热得快异常", use_container_width=True):
        synth.set_alarm_mode("101", DeviceStatus.ALARM_RESISTOR)
        st.toast(f"房间 101 已注入热得快波形", icon="🔥")

    if st.button("📻 注入微波炉异常", use_container_width=True):
        synth.set_alarm_mode("101", DeviceStatus.ALARM_MICROWAVE)
        st.toast(f"房间 101 已注入微波炉波形", icon="📻")

    if st.button("🤖 触发 AI 研判", use_container_width=True):
        trigger_ai_diagnosis("101")
        st.toast("AI 研判完成", icon="🤖")

    if st.button("✖ 清除所有异常", use_container_width=True):
        for rid in synth.ROOMS:
            synth.clear_alarm_mode(rid)
        st.toast("所有房间已恢复正常", icon="✅")
        st.rerun()

    if st.button("🔄 重置系统", use_container_width=True):
        synth.reset()
        store.reset()
        st.session_state.alarm_log = []
        st.session_state.agent_diagnoses = []
        st.session_state.ai_call_cooldown = {}
        st.toast("系统已重置", icon="🔄")
        st.rerun()

    # ── 系统状态 ──
    st.markdown("---")
    st.markdown("### 📡 系统状态")
    summary = store.get_building_summary()
    collector_status = "🟢 运行中" if st.session_state.get("collector_started") else "🔴 已停止"
    mqtt_count = len(broker.get_recent_messages(limit=100))
    alarm_count = summary.get("alarm_count", 0)
    warning_count = summary.get("warning_count", 0)

    st.caption(f"采集线程: {collector_status}")
    st.caption(f"MQTT 消息: {mqtt_count} 条")
    st.caption(f"告警: {alarm_count} · 预警: {warning_count}")
    st.caption(f"历史数据: {store.history_length} 个 tick")


@st.dialog("房间详情", width="large")
def show_room_detail(room_id: str):
    """显示房间详情弹窗"""
    # 获取房间数据
    room_history = store.get_room_history(room_id)
    power_array = store.get_power_array(room_id)

    if not room_history:
        st.warning("暂无数据")
        return

    latest = room_history[-1]
    power = latest.get("power", 0)
    voltage = latest.get("voltage", 0)
    smoke = latest.get("smoke_density", 0)

    # 房间基本信息
    st.markdown(f"### 🏠 Room {room_id}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("当前功率", f"{power:.1f}W")
    with col2:
        st.metric("电压", f"{voltage:.0f}V")
    with col3:
        st.metric("烟雾浓度", f"{smoke:.3f}ppm")
    with col4:
        status = get_status_text(power)
        st.metric("状态", status)

    # 历史波形图
    st.markdown("#### 📈 历史波形")
    if len(power_array) > 1:
        timestamps = [
            time.strftime("%H:%M:%S", time.localtime(time.time() - len(power_array) + i))
            for i in range(len(power_array))
        ]
        fig = build_power_chart(timestamps, power_array, room_id=room_id)
        st.plotly_chart(fig, use_container_width=True)

    # 波形特征
    if len(power_array) >= 3:
        st.markdown("#### 📊 波形特征")
        import numpy as np
        features = extract_waveform_features(np.array(power_array))

        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            st.metric("均值", f"{features['mean']:.1f}W")
        with col_f2:
            st.metric("标准差", f"{features['std']:.1f}")
        with col_f3:
            st.metric("最大值", f"{features['max']:.1f}W")
        with col_f4:
            st.metric("峰峰值", f"{features['ptp']:.1f}W")

    # AI 研判历史（如果有）
    room_diagnoses = [d for d in st.session_state.agent_diagnoses if d["room_id"] == room_id]
    if room_diagnoses:
        st.markdown("#### 🤖 AI 研判历史")
        for diag in room_diagnoses[:3]:
            with st.expander(f"`{diag['timestamp']}` - {diag['waveform_type']}"):
                st.markdown(diag["diagnosis"])

    # 操作按钮
    st.markdown("#### ⚡ 操作")
    col_op1, col_op2, col_op3 = st.columns(3)
    with col_op1:
        if st.button("🔥 注入热得快", key=f"detail_resistor_{room_id}"):
            synth.set_alarm_mode(room_id, DeviceStatus.ALARM_RESISTOR)
            st.toast(f"房间 {room_id} 已注入热得快波形", icon="🔥")
            st.rerun()
    with col_op2:
        if st.button("📻 注入微波炉", key=f"detail_microwave_{room_id}"):
            synth.set_alarm_mode(room_id, DeviceStatus.ALARM_MICROWAVE)
            st.toast(f"房间 {room_id} 已注入微波炉波形", icon="📻")
            st.rerun()
    with col_op3:
        if st.button("✖ 清除异常", key=f"detail_clear_{room_id}"):
            synth.clear_alarm_mode(room_id)
            st.toast(f"房间 {room_id} 已恢复正常", icon="✅")
            st.rerun()


def render_room_card(room: dict, room_history: list) -> None:
    """Render room card with alarm animation and trend indicator"""
    power = room["power"]
    status_text = get_status_text(power)

    # 根据状态添加 CSS 类
    if power > POWER_ALARM_THRESHOLD:
        card_class = "alarm-active"
        border_color = COLOR_ALARM
    elif power > POWER_WARNING_THRESHOLD:
        card_class = "warning-active"
        border_color = COLOR_WARNING
    else:
        card_class = "normal-state"
        border_color = COLOR_PRIMARY

    # 计算趋势
    power_array = store.get_power_array(room["id"])
    arrow, trend_color, delta = get_trend_info(power_array)
    delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"

    # 使用 HTML 渲染卡片(带动画效果)
    html_content = f'''
    <div class="{card_class}" style="border-radius: 8px; padding: 12px; margin-bottom: 8px; transition: all 0.3s ease;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: bold; font-size: 14px;">ROOM {room["id"]}</span>
            <span style="color: {border_color}; font-size: 12px;">{status_text}</span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 32px; font-weight: 700; color: {border_color}; font-variant-numeric: tabular-nums;">
                {power:.1f}<span style="font-size: 14px; color: {COLOR_TEXT_SECONDARY};"> W</span>
            </span>
            <span style="font-size: 14px; color: {trend_color}; font-weight: 600;">
                {arrow} {delta_str}W
            </span>
        </div>
        <div style="font-size: 11px; color: {COLOR_TEXT_SECONDARY};">
            {room["voltage"]:.0f}V · Smoke: {room["smoke_density"]:.3f}ppm
        </div>
    </div>
    '''
    st.markdown(html_content, unsafe_allow_html=True)

    # 迷你趋势线（用 plotly 很小的图）
    if len(room_history) > 1:
        recent = room_history[-20:]
        mini_fig = {
            "data": [{"y": recent, "type": "scatter", "mode": "lines",
                      "line": {"color": border_color, "width": 1.5},
                      "fill": "tozeroy",
                      "fillcolor": f"rgba(35, 142, 84, 0.1)"}],
            "layout": {
                "height": 30, "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
                "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
                "xaxis": {"visible": False}, "yaxis": {"visible": False},
                "showlegend": False,
            },
        }
        st.plotly_chart(mini_fig, use_container_width=True, key=f"spark_{room['id']}")

    # 详情按钮
    if st.button("📋 查看详情", key=f"detail_{room['id']}", use_container_width=True):
        show_room_detail(room['id'])


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
        summary = store.get_building_summary()
        runtime = time.time() - st.session_state.get("start_time", time.time())
        runtime_str = time.strftime("%H:%M:%S", time.gmtime(runtime))

        st.markdown(f"### 🏠 {settings.building_name} 安全监控")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("总房间数", f"{summary['total_rooms']}")
        with c2:
            st.metric("总功率", f"{summary['total_power']:.0f}W")
        with c3:
            st.metric("平均功率", f"{summary['avg_power']:.0f}W")
        with c4:
            alarm_count = summary['alarm_count']
            st.metric("告警", f"{alarm_count}", delta=f"{alarm_count} 严重" if alarm_count > 0 else None,
                       delta_color="inverse" if alarm_count > 0 else "off")
        with c5:
            st.metric("运行时长", runtime_str)

        # 告警横幅
        alarm_count = summary.get("alarm_count", 0)
        warning_count = summary.get("warning_count", 0)
        if alarm_count > 0:
            # 找出告警房间
            snapshot = store.latest_snapshot
            alarm_rooms = [rid for rid, d in snapshot.items() if d.get("power", 0) > POWER_ALARM_THRESHOLD]
            rooms_str = "、".join(alarm_rooms[:3])
            st.markdown(
                f'<div class="alarm-banner">'
                f'🚨 <b>检测到 {alarm_count} 个房间告警！</b> '
                f'房间 {rooms_str} 功率异常偏高，请立即检查！'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif warning_count > 0:
            snapshot = store.latest_snapshot
            warning_rooms = [rid for rid, d in snapshot.items()
                             if POWER_WARNING_THRESHOLD < d.get("power", 0) <= POWER_ALARM_THRESHOLD]
            rooms_str = "、".join(warning_rooms[:3])
            st.markdown(
                f'<div class="warning-banner">'
                f'⚠️ <b>{warning_count} 个房间预警</b> '
                f'房间 {rooms_str} 功率偏高，请关注'
                f'</div>',
                unsafe_allow_html=True,
            )

    status_bar()

    # ── 楼层选择器 ──
    col_floor_select, _ = st.columns([1, 3])
    with col_floor_select:
        selected_floor = st.selectbox(
            "选择楼层",
            synth.floors,
            format_func=lambda x: f"{x}F",
            key="selected_floor",
        )

    # ── 整栋楼概览图 ──
    @st.fragment(run_every="1s")
    def building_overview():
        snapshot = store.latest_snapshot
        all_rooms_data = build_room_grid_data(snapshot)
        fig = build_building_overview(all_rooms_data, settings.building_floors, settings.rooms_per_floor)
        st.plotly_chart(fig, use_container_width=True, key="building_overview")

    building_overview()

    # ── 主体：左侧 Agent + 右侧楼层详情 ──
    col_agent, col_floor = st.columns([1, 3])

    # 左侧：AI Agent（静态，不自动刷新）
    with col_agent:
        st.markdown("#### 🤖 AI Agent")
        st.caption("推理层: 波形分类 → LLM 研判")

        if st.session_state.agent_diagnoses:
            latest = st.session_state.agent_diagnoses[0]
            st.markdown(f"**最新研判** `{latest['timestamp']}`")
            st.markdown(f"Room **{latest['room_id']}** · `{latest['waveform_type']}`")

            # 显示波形特征
            import numpy as np
            features = extract_waveform_features(np.array(latest["power_array"]))

            # AI 推理流程图
            st.markdown("**推理流程**")
            reasoning_fig = build_ai_reasoning_chart(
                latest["waveform_type"],
                features,
                latest["diagnosis"]
            )
            st.plotly_chart(reasoning_fig, use_container_width=True, key="reasoning_chart")

            # 特征指标
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                st.metric("均值", f"{features['mean']:.0f}W")
            with col_f2:
                st.metric("标准差", f"{features['std']:.1f}")
            with col_f3:
                st.metric("峰峰值", f"{features['ptp']:.0f}W")

            st.info(latest["diagnosis"])
        else:
            st.caption("暂无研判 — 使用「配置中心」触发异常")

        if len(st.session_state.agent_diagnoses) > 1:
            with st.expander(f"📜 历史研判 ({len(st.session_state.agent_diagnoses)} 条)"):
                for diag in st.session_state.agent_diagnoses[1:6]:
                    st.caption(f"`{diag['timestamp']}` · Room {diag['room_id']}")

    # 右侧：当前楼层详情（局部刷新）
    with col_floor:
        @st.fragment(run_every="1s")
        def floor_detail():
            # 获取当前楼层的房间
            floor_rooms = synth.get_rooms_on_floor(selected_floor)
            floor_snapshot = store.get_floor_snapshot(selected_floor)
            floor_rooms_data = build_room_grid_data(floor_snapshot)

            # 楼层平面图
            st.markdown(f"#### {selected_floor}F 楼层平面图")
            fig = build_floor_plan_chart(floor_rooms_data)
            st.plotly_chart(fig, use_container_width=True, key=f"floor_{selected_floor}")

            # 房间卡片网格（3列 x 2行）
            st.markdown(f"#### {selected_floor}F 房间状态")
            for row in range(2):
                cols = st.columns(3)
                for col_idx in range(3):
                    room_idx = row * 3 + col_idx
                    if room_idx < len(floor_rooms_data):
                        room = floor_rooms_data[room_idx]
                        with cols[col_idx]:
                            history = store.get_power_array(room["id"])
                            render_room_card(room, history)

        floor_detail()

        # 房间选择器（用于查看详细波形）
        floor_rooms = synth.get_rooms_on_floor(selected_floor)
        selected_room = st.selectbox(
            "选择房间查看详细波形",
            floor_rooms,
            key="chart_room",
        )

    # ── 底部：历史趋势 + 波形图 + MQTT 日志（局部刷新）──
    st.markdown("---")

    @st.fragment(run_every="1s")
    def bottom_panel():
        # 历史趋势分析
        st.markdown("#### 📈 历史趋势分析")
        floor_rooms = synth.get_rooms_on_floor(selected_floor)
        rooms_history = {}
        for room_id in floor_rooms[:6]:  # 最多显示6个房间
            history = store.get_power_array(room_id)
            if history:
                rooms_history[room_id] = history

        if rooms_history:
            # 生成时间戳
            max_len = max(len(h) for h in rooms_history.values())
            trend_timestamps = [
                time.strftime("%H:%M:%S", time.localtime(time.time() - max_len + i))
                for i in range(max_len)
            ]
            trend_fig = build_history_trend_chart(rooms_history, timestamps=trend_timestamps)
            st.plotly_chart(trend_fig, use_container_width=True, key="history_trend")
        else:
            st.info("暂无历史数据...")

        # 波形图 + MQTT 日志
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
                    room_id = topic.split('/')[-2]
                    # 根据功率添加类型图标
                    if power > POWER_ALARM_THRESHOLD:
                        icon = "🔴"
                        st.markdown(f":red[{icon} `{room_id}` **{power:.1f}W** ⚠告警]")
                    elif power > POWER_WARNING_THRESHOLD:
                        icon = "🟡"
                        st.markdown(f":orange[{icon} `{room_id}` **{power:.1f}W** ⚡预警]")
                    else:
                        icon = "🟢"
                        st.caption(f"{icon} `{room_id}` {power:.1f}W")

            if st.session_state.alarm_log:
                st.markdown("**🚨 AI 告警**")
                for entry in st.session_state.alarm_log[:3]:
                    st.markdown(f":red[⚠ Room {entry['room_id']}] {entry['power']:.0f}W")
                    if entry.get("diagnosis"):
                        st.caption(entry["diagnosis"][:80] + "..." if len(entry.get("diagnosis", "")) > 80 else entry.get("diagnosis", ""))

    bottom_panel()


# ═══════════════════════════════════════════════════════════
#  Tab 2: 配置中心
# ═══════════════════════════════════════════════════════════

with tab_config:
    st.markdown("### ⚙ 配置中心")

    # ── 系统架构图 ──
    st.markdown("#### 🏗️ 系统架构")
    arch_fig = build_architecture_diagram()
    st.plotly_chart(arch_fig, use_container_width=True, key="architecture")

    st.markdown("---")

    # ── 能耗统计报表 ──
    st.markdown("#### 📊 能耗统计")
    all_rooms_history = {}
    for room_id in synth.ROOMS:
        power_array = store.get_power_array(room_id)
        if power_array:
            all_rooms_history[room_id] = power_array

    if all_rooms_history:
        energy_fig = build_energy_statistics_chart(all_rooms_history)
        st.plotly_chart(energy_fig, use_container_width=True, key="energy_stats")

        # 统计摘要（带环比）
        total_power = sum(sum(h) for h in all_rooms_history.values())
        total_samples = sum(len(h) for h in all_rooms_history.values())
        avg_power = total_power / total_samples if total_samples > 0 else 0
        max_power = max(max(h) for h in all_rooms_history.values())
        active_rooms = len([h for h in all_rooms_history.values() if h[-1] > 100])

        # 计算环比（最近 30 个点 vs 之前的 30 个点）
        recent_total = 0
        prev_total = 0
        recent_count = 0
        prev_count = 0
        for h in all_rooms_history.values():
            if len(h) >= 60:
                recent_total += sum(h[-30:])
                prev_total += sum(h[-60:-30])
                recent_count += 30
                prev_count += 30
            elif len(h) >= 30:
                recent_total += sum(h[-30:])
                recent_count += 30

        recent_avg = recent_total / recent_count if recent_count > 0 else avg_power
        prev_avg = prev_total / prev_count if prev_count > 0 else avg_power
        power_delta = recent_avg - prev_avg

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("总能耗", f"{total_power:.0f}W")
        with col_stat2:
            st.metric("平均功率", f"{avg_power:.0f}W",
                       delta=f"{power_delta:+.1f}W" if prev_count > 0 else None)
        with col_stat3:
            st.metric("最大功率", f"{max_power:.0f}W")
        with col_stat4:
            st.metric("活跃房间", f"{active_rooms}")
    else:
        st.info("暂无历史数据...")

    st.markdown("---")

    # ── 数据导出 ──
    st.markdown("#### 📥 数据导出")
    col_export1, col_export2, col_export3 = st.columns(3)

    with col_export1:
        if st.button("📊 导出当前楼层数据 (CSV)", use_container_width=True):
            # 获取当前楼层数据
            floor_snapshot = store.get_floor_snapshot(selected_floor)
            if floor_snapshot:
                import pandas as pd
                import io

                # 转换为 DataFrame
                df = pd.DataFrame.from_dict(floor_snapshot, orient='index')
                df.index.name = 'room_id'
                df.insert(0, "export_time", time.strftime("%Y-%m-%d %H:%M:%S"))

                # 转换为 CSV
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer)

                # 提供下载
                st.download_button(
                    label="下载 CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"floor_{selected_floor}_data_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("暂无数据")

    with col_export2:
        if st.button("📈 导出历史趋势 (CSV)", use_container_width=True):
            # 获取所有房间的历史数据
            all_history = {}
            for room_id in synth.ROOMS:
                power_array = store.get_power_array(room_id)
                if power_array:
                    all_history[room_id] = power_array

            if all_history:
                import pandas as pd
                import io

                # 转换为 DataFrame（对齐长度，带时间戳）
                max_len = max(len(v) for v in all_history.values())
                timestamps = [
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - max_len + i))
                    for i in range(max_len)
                ]
                df_data = {"timestamp": timestamps}
                for room_id, values in all_history.items():
                    df_data[room_id] = values + [None] * (max_len - len(values))

                df = pd.DataFrame(df_data)

                # 转换为 CSV
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)

                # 提供下载
                st.download_button(
                    label="下载 CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"history_trend_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("暂无历史数据")

    with col_export3:
        if st.button("🤖 导出 AI 研判记录 (JSON)", use_container_width=True):
            if st.session_state.agent_diagnoses:
                import json

                # 添加导出元数据
                export_data = {
                    "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "building": settings.building_name,
                    "total_records": len(st.session_state.agent_diagnoses),
                    "diagnoses": st.session_state.agent_diagnoses,
                }
                json_data = json.dumps(export_data, ensure_ascii=False, indent=2)

                # 提供下载
                st.download_button(
                    label="下载 JSON",
                    data=json_data,
                    file_name=f"ai_diagnoses_{time.strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            else:
                st.warning("暂无研判记录")

    st.markdown("---")

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
