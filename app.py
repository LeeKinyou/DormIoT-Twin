"""DormIoT-Twin — 宿舍物联网安全监控数字孪生系统

启动方式：uv run streamlit run app.py
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime

import streamlit as st
from loguru import logger
from streamlit_echarts import st_echarts

from dormiot.config import settings
from dormiot.gateway.mqtt_handler import MQTTHandler
from dormiot.gateway.rule_engine import RuleEngine
from dormiot.gateway.pipeline import DataPipeline
from dormiot.schemas.alert import AlertLevel
from dormiot.schemas.device import DeviceStatus, MeterReport
from dormiot.simulation.cluster import ClusterConfig, SimulationCluster
from dormiot.simulation.publisher import MQTTPublisher
from dormiot.storage.redis_cache import RedisCache
from dormiot.storage.repository import AlertRepository
from dormiot.ui.charts import power_trend_option, room_power_option, status_pie_option
from dormiot.ui.floor_plan import render_floor_plan_html

# ── 页面配置 ──
st.set_page_config(
    page_title="DormIoT-Twin 安全监控",
    page_icon="🔥",
    layout="wide",
)

# ── 集群配置 ──
CLUSTER_CONFIG = ClusterConfig()
ALL_BUILDINGS = list(CLUSTER_CONFIG.buildings.keys())

# ── 线程安全的共享缓冲区（MQTT 线程写入，Streamlit 主线程读取） ──
_shared_lock = threading.Lock()
_shared_device_status: dict[str, dict] = {}
_shared_power_history: dict[str, list] = {"timestamps": [], "values": []}
_shared_room_history: dict[str, dict[str, list]] = defaultdict(lambda: {"timestamps": [], "values": []})
_shared_message_count = 0
_sim_running = threading.Event()


def _on_mqtt_message(report: MeterReport) -> None:
    """MQTT 消息回调（在后台线程执行）— 只写共享缓冲区，不碰 st.session_state"""
    global _shared_message_count
    now = datetime.now().strftime("%H:%M:%S")
    device_id = report.device_id
    data = {
        "status": report.status.value,
        "current_power": str(report.metrics.current_power),
        "voltage": str(report.metrics.voltage),
        "smoke_density": str(report.metrics.smoke_density),
        "timestamp": report.timestamp,
    }

    with _shared_lock:
        _shared_device_status[device_id] = data
        _shared_message_count += 1

        # 全校功率历史（保留最近 200 个点）
        _shared_power_history["timestamps"].append(now)
        _shared_power_history["values"].append(report.metrics.current_power)
        if len(_shared_power_history["timestamps"]) > 200:
            _shared_power_history["timestamps"] = _shared_power_history["timestamps"][-200:]
            _shared_power_history["values"] = _shared_power_history["values"][-200:]

        # 单房间历史
        room_hist = _shared_room_history[device_id]
        room_hist["timestamps"].append(now)
        room_hist["values"].append(report.metrics.current_power)
        if len(room_hist["timestamps"]) > 200:
            room_hist["timestamps"] = room_hist["timestamps"][-200:]
            room_hist["values"] = room_hist["values"][-200:]


# ── 初始化 session state ──
def init_session_state():
    for key, default in [
        ("device_status", {}),
        ("power_history", {"timestamps": [], "values": []}),
        ("room_history", defaultdict(lambda: {"timestamps": [], "values": []})),
        ("pipeline_started", False),
        ("message_count", 0),
        ("selected_building", ALL_BUILDINGS[0]),
        ("selected_room", None),
        ("sim_cluster", None),
        ("sim_running", False),
        ("sim_publisher", None),
        ("sim_thread", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _sync_shared_to_session():
    """从线程安全缓冲区同步数据到 st.session_state（必须在主线程调用）"""
    global _shared_message_count
    with _shared_lock:
        if not _shared_device_status:
            return
        st.session_state.device_status = dict(_shared_device_status)
        st.session_state.message_count = _shared_message_count

        # 同步功率历史
        st.session_state.power_history = {
            "timestamps": list(_shared_power_history["timestamps"]),
            "values": list(_shared_power_history["values"]),
        }

        # 同步房间历史
        for device_id, hist in _shared_room_history.items():
            st.session_state.room_history[device_id] = {
                "timestamps": list(hist["timestamps"]),
                "values": list(hist["values"]),
            }


# ── 启动数据管线 ──
def start_pipeline():
    if st.session_state.pipeline_started:
        return
    try:
        handler = MQTTHandler(
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            topic=settings.mqtt_topic_pattern,
        )
        rule_engine = RuleEngine()
        redis_cache = RedisCache()
        alert_repo = AlertRepository()
        pipeline = DataPipeline(handler, rule_engine, redis_cache, alert_repo)
        # 将 UI 回调注册到管线，管线内部会串联：缓存 → 规则 → MySQL → UI
        pipeline.on_message_callback = _on_mqtt_message
        pipeline.start()
        st.session_state.pipeline = pipeline
        st.session_state.pipeline_started = True
        logger.info("数据管线已启动")
    except Exception as e:
        st.warning(f"数据管线启动失败（MQTT/Redis/MySQL 可能未运行）: {e}")


# ── 仪表盘指标卡片 ──
def render_dashboard():
    device_status = st.session_state.device_status
    total = len(device_status)
    normal = sum(1 for d in device_status.values() if d["status"] == "NORMAL")
    warning = sum(1 for d in device_status.values() if d["status"] == "WARNING")
    alarm = sum(1 for d in device_status.values() if d["status"] == "ALARM")
    total_power = sum(float(d.get("current_power", 0)) for d in device_status.values())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("在线设备", total)
    col2.metric("正常", normal)
    col3.metric("预警", warning, delta=f"-{warning}" if warning > 0 else None)
    col4.metric("告警", alarm, delta=f"-{alarm}" if alarm > 0 else None, delta_color="inverse")
    col5.metric("总功率", f"{total_power:.0f} W")


# ── 全校功率趋势图 ──
def render_power_chart():
    history = st.session_state.power_history
    if not history["timestamps"]:
        st.info("等待数据...")
        return
    option = power_trend_option(history["timestamps"], history["values"])
    st_echarts(option, height="350px", key="power_trend")


# ── 设备状态饼图 ──
def render_status_pie():
    device_status = st.session_state.device_status
    normal = sum(1 for d in device_status.values() if d["status"] == "NORMAL")
    warning = sum(1 for d in device_status.values() if d["status"] == "WARNING")
    alarm = sum(1 for d in device_status.values() if d["status"] == "ALARM")
    option = status_pie_option(normal, warning, alarm)
    st_echarts(option, height="300px", key="status_pie")


# ── 楼层平面图 ──
def render_floor_plan():
    building_id = st.session_state.selected_building
    rooms = CLUSTER_CONFIG.buildings.get(building_id, [])
    device_status = st.session_state.device_status
    selected_room = st.session_state.selected_room

    html = render_floor_plan_html(building_id, rooms, device_status, selected_room)
    st.iframe(html, height=350)

    query_params = st.query_params
    if "room" in query_params:
        room = query_params["room"]
        if room in rooms:
            st.session_state.selected_room = room


# ── 房间详情面板 ──
def render_room_detail():
    room = st.session_state.selected_room
    if not room:
        st.info("点击楼层平面图中的房间查看详情")
        return

    building_id = st.session_state.selected_building
    device_id = f"MOCK_METER_BLDG{building_id}_RM{room}"
    info = st.session_state.device_status.get(device_id)

    st.subheader(f"{building_id}号楼 {room} 房间详情")
    if not info:
        st.warning("暂无该房间数据")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("状态", info["status"])
    c2.metric("功率", f"{float(info['current_power']):.1f} W")
    c3.metric("电压", f"{float(info['voltage']):.1f} V")
    c4.metric("烟雾浓度", f"{float(info['smoke_density']):.4f} ppm")

    room_hist = st.session_state.room_history.get(device_id, {"timestamps": [], "values": []})
    if room_hist["timestamps"]:
        option = room_power_option(room_hist["timestamps"], room_hist["values"], room)
        st_echarts(option, height="300px", key=f"room_chart_{room}")


# ── 告警记录页面 ──
def render_alert_page():
    st.subheader("告警记录查询")

    col1, col2, col3 = st.columns(3)
    with col1:
        level_filter = st.selectbox("告警级别", ["全部", "CRITICAL", "HIGH", "MEDIUM"], index=0)
    with col2:
        building_filter = st.selectbox("楼栋", ["全部"] + ALL_BUILDINGS, index=0)
    with col3:
        resolved_filter = st.selectbox("处理状态", ["全部", "未处理", "已处理"], index=0)

    try:
        repo = AlertRepository()
        level = AlertLevel(level_filter) if level_filter != "全部" else None
        building = building_filter if building_filter != "全部" else None
        resolved = None if resolved_filter == "全部" else (resolved_filter == "已处理")
        alerts = repo.query_alerts(alert_level=level, building_id=building, resolved=resolved, limit=200)
        repo.close()

        if not alerts:
            st.info("暂无告警记录")
            return

        rows = []
        for a in alerts:
            rows.append({
                "ID": a.id,
                "设备": a.device_id,
                "楼栋": a.building_id,
                "房间": a.room_id,
                "级别": a.alert_level,
                "类型": a.alert_type,
                "消息": a.message,
                "时间": datetime.fromtimestamp(a.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                "已处理": "✅" if a.resolved else "❌",
            })
        st.dataframe(rows, width='stretch')

        st.markdown("---")
        st.subheader("标记告警已处理")
        alert_id = st.number_input("告警 ID", min_value=1, step=1)
        if st.button("标记已处理"):
            repo2 = AlertRepository()
            if repo2.resolve_alert(alert_id):
                st.success(f"告警 #{alert_id} 已标记为已处理")
                st.rerun()
            else:
                st.error("告警 ID 不存在")
            repo2.close()
    except Exception as e:
        st.warning(f"MySQL 连接失败: {e}")


# ── 仿真循环（后台线程） ──
def simulation_loop(cluster: SimulationCluster, publisher: MQTTPublisher, interval_s: float):
    while _sim_running.is_set():
        try:
            reports = cluster.generate_all()
            for report in reports:
                publisher.publish(report)
        except Exception as e:
            logger.error(f"仿真发布失败: {e}")
        time.sleep(interval_s)


# ── 仿真控制页面 ──
def render_simulation_page():
    st.subheader("仿真控制面板")

    if st.session_state.sim_cluster is None:
        st.session_state.sim_cluster = SimulationCluster(CLUSTER_CONFIG)

    cluster = st.session_state.sim_cluster

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶ 启动仿真", disabled=st.session_state.sim_running, width='stretch'):
            try:
                publisher = MQTTPublisher(
                    broker_host=settings.mqtt_broker_host,
                    broker_port=settings.mqtt_broker_port,
                )
                publisher.connect()
                st.session_state.sim_publisher = publisher
                st.session_state.sim_running = True
                _sim_running.set()
                interval_s = settings.simulation_report_interval_ms / 1000.0
                thread = threading.Thread(
                    target=simulation_loop,
                    args=(cluster, publisher, interval_s),
                    daemon=True,
                    name="sim-publisher",
                )
                thread.start()
                st.session_state.sim_thread = thread
                st.success(f"仿真已启动（每 {interval_s}s 发布一轮）")
                st.rerun()
            except Exception as e:
                st.error(f"启动失败: {e}")

    with col2:
        if st.button("⏹ 停止仿真", disabled=not st.session_state.sim_running, width='stretch'):
            _sim_running.clear()
            if st.session_state.sim_publisher:
                st.session_state.sim_publisher.disconnect()
            st.session_state.sim_publisher = None
            st.session_state.sim_running = False
            st.success("仿真已停止")
            st.rerun()

    with col3:
        if st.button("🔄 重置所有设备", width='stretch'):
            cluster.reset_all()
            st.success("所有设备已重置为 NORMAL")
            st.rerun()

    st.markdown("---")
    st.markdown(f"**设备总数**: {cluster.device_count} | **仿真状态**: {'运行中 ▶' if st.session_state.sim_running else '已停止 ⏹'}")
    st.markdown("---")

    st.subheader("异常注入")
    device_ids = list(cluster.devices.keys())

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        target_device = st.selectbox("目标设备", device_ids, index=0)
    with col_b:
        inject_state = st.selectbox("注入状态", ["WARNING", "ALARM"], index=1)
    with col_c:
        st.markdown("&nbsp;")
        if st.button("💉 注入异常", width='stretch'):
            state = DeviceStatus(inject_state)
            if cluster.inject_anomaly(target_device, state):
                st.success(f"已向 {target_device} 注入 {inject_state}")
            else:
                st.error("注入失败")

    st.markdown("---")
    st.subheader("设备状态一览")
    device_rows = []
    for device_id, device in cluster.devices.items():
        parts = device_id.split("_")
        building = parts[2].replace("BLDG", "") if len(parts) > 2 else ""
        room = parts[3].replace("RM", "") if len(parts) > 3 else ""
        device_rows.append({
            "设备ID": device_id,
            "楼栋": building,
            "房间": room,
            "状态": device.state.value,
        })
    st.dataframe(device_rows, width='stretch', height=300)


# ── 主应用 ──
def main():
    init_session_state()
    start_pipeline()

    st.title("🔥 DormIoT-Twin 宿舍安全监控")

    col_sel, _ = st.columns([1, 3])
    with col_sel:
        st.session_state.selected_building = st.selectbox("选择楼栋", ALL_BUILDINGS, index=0)

    @st.fragment(run_every="2s")
    def auto_refresh():
        _sync_shared_to_session()
        render_dashboard()
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            render_power_chart()
        with c2:
            render_status_pie()
        st.markdown("---")
        c3, c4 = st.columns([1, 1])
        with c3:
            render_floor_plan()
        with c4:
            render_room_detail()

    tab1, tab2, tab3 = st.tabs(["实时监控", "告警记录", "仿真控制"])
    with tab1:
        auto_refresh()
    with tab2:
        render_alert_page()
    with tab3:
        render_simulation_page()


if __name__ == "__main__":
    main()
