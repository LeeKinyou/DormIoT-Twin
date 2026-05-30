# DormIoT-Twin 产品说明文档

> 基于数字孪生的全景宿舍物联网安全监控系统

---

## 1. 项目概述

### 1.1 背景与痛点

高校宿舍安全管理中，违章大功率电器（热得快、大功率电吹风、电暖器等）的私自使用极易引发电闸过载甚至火灾。传统物联网监控系统开发高度依赖物理硬件调试，在校园场景落地时面临：

| 痛点 | 说明 |
|------|------|
| **权限受限** | 学生或普通开发人员无法私自拆配宿舍强电电闸加装物理电流传感器 |
| **规模化测试难** | 受限于硬件经费，物理开发板通常只能测试 1-2 个节点，无法验证大规模高并发场景 |

### 1.2 核心理念

本系统采用 **软件定义物联网（SD-IoT）** 与 **数字孪生（Digital Twin）** 理念：

- 感知层通过"数字孪生节点集群"高仿真还原物理电表数据波形，实现无硬件内耗的高效开发
- 网络层与应用层完全基于标准物联网协议（MQTT）与工业级数据契约建设
- 具备 **虚实无缝平替** 特性：未来将相同逻辑的 MQTT 客户端代码烧录进物理电表（如 ESP32 智能电表），即可"即插即用"式切换，后端无需改动任何代码

---

## 2. 系统总体架构

系统严格遵循标准物联网三层架构（感知层 → 网络层 → 应用层）进行闭环设计：

```
┌─────────────────────────────────────────────────────────────┐
│              感知层：DormIoT-Twin 分布式仿真集群              │
│   [宿舍电表线程 1]  [宿舍电表线程 2]  [宿舍电表线程 3] ... N  │
└────────────────────────┬────────────────────────────────────┘
                         │  标准 MQTT 协议 / JSON 载荷
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               网络层：高性能物联网消息网关                    │
│             [ EMQX Message Broker (Docker 部署) ]            │
└────────────────────────┬────────────────────────────────────┘
                         │  通配符主题路由分发
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              应用层：业务核心网关与大屏中心                    │
│  ┌─────────────────┐    ┌──────────────────────────────┐    │
│  │ 核心数据摄取网关  │───▶│   宿管全景实时监控大屏        │    │
│  │ (异步事件/规则引擎)│    │  (数据大屏/ECharts 动态折线)  │    │
│  └────────┬────────┘    └──────────────────────────────┘    │
└───────────│─────────────────────────────────────────────────┘
            ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据存储层                            │
│   [ Redis 缓存：最新瞬时状态 ]   [ MySQL：历史告警日志 ]      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 感知层设计

### 3.1 多线程仿真模型

每个宿舍的智能电表抽象为独立类 `VirtualIoTDevice`，运行在独立线程/协程中。通过传入不同配置参数（楼栋号、房间号），动态构建覆盖全校的大规模虚拟感知集群。

### 3.2 物理行为仿真算法

摒弃简单随机数生成，引入 **基准值 + 高斯随机扰动** 算法：

- **常态能耗仿真**：模拟空气流动、供电电压微小浮动带来的日光灯及充电器功率起伏（如 50W 基础负载上叠加 ±2W 高斯噪声）
- **状态机转换演练**：每个节点内置状态机，可通过外部指令或随机概率切换至"突发高负载"或"火灾隐患"状态，使电流波形和烟雾浓度瞬时飙升

### 3.3 统一数据契约（JSON Schema）

所有虚拟/物理节点上报的数据必须遵守以下标准格式：

```json
{
  "device_id": "MOCK_METER_BLDG5_RM402",
  "timestamp": 1716987600,
  "metrics": {
    "current_power": 2150.5,
    "voltage": 220.4,
    "smoke_density": 0.02
  },
  "status": "NORMAL"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | String | 设备唯一标识，全局唯一 |
| `timestamp` | Integer | 秒级 UNIX 时间戳 |
| `metrics.current_power` | Float | 当前宿舍总功率 (W) |
| `metrics.voltage` | Float | 当前供电电压 (V) |
| `metrics.smoke_density` | Float | 烟雾浓度探测值 (ppm) |
| `status` | String | 设备自检状态：NORMAL / WARNING / ALARM |

---

## 4. 网络层设计

### 4.1 消息网关选型

采用开源高性能分布式物联网消息服务器 **EMQX**（Docker 一键部署），承载感知层海量并发节点的 TCP 长连接，实现消息毫秒级路由分发。

### 4.2 Topic 主题拓扑

采用树形主题架构，具备高扩展性与行政区划隔离能力：

**命名规范**：`campus/{building_id}/{room_id}/meter`

**示例**：
- `campus/building5/room401/meter` — 5 号楼 401 宿舍电表
- `campus/building12/room302/meter` — 12 号楼 302 宿舍电表

**路由优势**：应用层后端只需订阅通配符主题 `campus/+/+/meter`，即可单条管道动态摄取全校所有宿舍的实时能耗数据。

---

## 5. 应用层设计

### 5.1 数据摄取网关

后端作为标准 MQTT 消费者接入 EMQX 代理，采用 **异步非阻塞（Async/Await）** 事件循环机制，毫秒级完成解析，避免高频并发下的丢包问题。

### 5.2 规则引擎

网关解析 JSON 报文后，数据进入内置规则引擎进行条件匹配：

| 告警级别 | 触发条件 | 判定结果 |
|---------|---------|---------|
| **火灾特级** | `smoke_density > 0.40` 或 `status == "ALARM_FIRE"` | 立即触发最高级别响应 |
| **违章电器** | `current_power > 1500W` | 宿舍正在使用违章电器（如热得快） |
| **恶性负载** | `current_power > 800W` 且持续时间 > 60 分钟 | 存在恶意持续负载 |

### 5.3 双层数据存储策略

采用"读写分离、冷热分层"架构：

- **Redis（高速缓存层）**：Hash 结构存储全校每个宿舍最新瞬时状态，Key 格式 `cache:dorm:{building_id}:{room_id}`，内存级响应，保护主数据库
- **MySQL（持久化存储层）**：仅在规则引擎触发告警或每日能耗结算时异步写入 `security_alerts` 表，不记录常态数据

### 5.4 实时数据更新

基于 Streamlit 原生机制实现实时刷新：利用 `@st.fragment` 装饰器配合 `run_every` 参数，对监控大屏中的关键区域实现秒级自动刷新，无需手动 WebSocket 管理。MQTT 后台线程持续将最新数据写入 `st.session_state`，fragment 每次重绘时读取最新状态。

### 5.5 宿管全景监控大屏

前端完全基于 Streamlit + streamlit-echarts + SVG 楼层平面图构建：

- **SVG 楼层平面图**：以 2D 平面图还原每层楼的宿舍布局，每个房间为一个色块（正常=绿、警告=黄、告警=红、离线=灰），点击任意房间弹出详情面板，展示实时指标 + 今日功率走势折线图
- **全校能耗总览**：streamlit-echarts 渲染全校总功率实时折线图，支持各楼栋对比柱状图

---

## 6. 工程亮点

### 大规模并发与压力验证

采用软件定义物联网，在单台机器上跑通 50+ 分布式宿舍节点同时在线的高并发场景，技术重心提升至后端网关吞吐量、Redis 缓存设计及规则引擎性能优化。

### 完全物联网标准解耦（支持无缝硬件平替）

数据链条和通信协议完全透明。未来只需使真实智能电表按 JSON 契约向网络层发包，即可一秒钟从"数字孪生"切换到"物理实体"，后端零改动。

### 闭环混沌演练机制（Chaos Engineering）

感知层设计异常状态机演练算法，完整模拟 **"突发火灾 → 数据突变 → 网关路由 → 规则引擎毫秒匹配 → 前端大屏红字闪烁报警"** 的安全控制链路，无需真实危险操作即可完成端到端验证。

---

## 7. 技术栈概览

| 层级 | 技术选型 |
|------|---------|
| 感知层 | Python asyncio 协程、高斯噪声仿真、状态机 |
| 网络层 | EMQX (Docker)、MQTT 协议、树形 Topic 路由 |
| 应用层 | Streamlit 全栈框架、规则引擎、后台线程 MQTT 监听 |
| 存储层 | Redis（缓存）、MySQL（持久化） |
| 前端 | Streamlit + streamlit-echarts（ECharts）+ HTML 楼层平面图 |
| 包管理 | uv（依赖管理 + 项目运行） |

---

## 8. 架构设计详述（Streamlit 全栈方案）

### 8.1 技术栈明细与选型依据

| 类别 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| **语言** | Python | 3.12+ | 原生 async/await、类型提示成熟 |
| **包管理** | uv | 0.5+ | 极速依赖解析，`uv run` 一键运行，替代 pip/poetry |
| **全栈框架** | Streamlit | 1.40+ | 纯 Python 构建交互式 Web 应用，无需前端工程化 |
| **MQTT 客户端** | paho-mqtt | 1.6+ | MQTT 标准客户端，配合 `threading` 实现后台持续监听 |
| **ORM** | SQLAlchemy | 2.0+ | 声明式模型定义，连接池管理 |
| **数据库驱动** | PyMySQL | 1.1+ | MySQL 同步驱动，兼容 Streamlit 同步模型 |
| **Redis 客户端** | redis-py | 5.0+ | 同步接口，Streamlit 每次 rerun 时快速读取缓存 |
| **数据校验** | Pydantic | v2 | 运行时类型校验，与 MQTT 报文解析强绑定 |
| **图表** | streamlit-echarts | 0.4+ | ECharts 的 Streamlit 封装，支持动态折线图 |
| **HTML 渲染** | `st.components.v1.html` | 内置 | 渲染自定义 SVG 楼层平面图，支持交互事件回传 |
| **日志** | loguru | 0.7+ | 结构化日志、零配置旋转归档 |
| **容器化** | Docker + Docker Compose | 24.x / 2.x | 仅编排基础设施（EMQX / Redis / MySQL） |

### 8.2 项目目录结构

```
DormIoT-Twin/
├── pyproject.toml                 # 项目元数据与 uv 依赖声明
├── uv.lock                        # uv 锁定文件（自动生成）
├── docker-compose.yml             # 仅基础设施：EMQX / Redis / MySQL
├── .env.example                   # 环境变量模板
│
├── src/
│   └── dormiot/
│       ├── __init__.py
│       ├── config.py              # Pydantic Settings 配置管理
│       │
│       ├── simulation/            # ── 感知层：数字孪生仿真集群 ──
│       │   ├── __init__.py
│       │   ├── device.py          # VirtualIoTDevice 核心类
│       │   ├── noise.py           # 高斯噪声 & 信号扰动算法
│       │   ├── state_machine.py   # 设备状态机（NORMAL/WARNING/ALARM）
│       │   └── cluster.py         # 仿真集群编排器（批量启停、动态扩缩）
│       │
│       ├── gateway/               # ── 网络层 & 应用层 ──
│       │   ├── __init__.py
│       │   ├── mqtt_handler.py    # MQTT 后台线程监听、报文解析
│       │   └── rule_engine.py     # 规则引擎（阈值匹配、告警分级）
│       │
│       ├── storage/               # ── 数据存储层 ──
│       │   ├── __init__.py
│       │   ├── redis_cache.py     # Redis 同步缓存操作封装
│       │   ├── models.py          # SQLAlchemy ORM 模型定义
│       │   └── repository.py      # 数据访问层（告警日志 CRUD）
│       │
│       ├── ui/                    # ── Streamlit UI 组件 ──
│       │   ├── __init__.py
│       │   ├── floor_plan.py      # SVG 楼层平面图渲染 & 交互
│       │   ├── charts.py          # ECharts 图表封装
│       │   └── components.py      # 通用 UI 组件（告警卡片、指标面板）
│       │
│       └── schemas/               # ── Pydantic 数据契约 ──
│           ├── __init__.py
│           ├── device.py          # 设备上报数据 Schema
│           └── alert.py           # 告警数据 Schema
│
├── app.py                         # Streamlit 主入口（概览仪表盘）
├── pages/                         # Streamlit 多页面
│   ├── 1_楼层监控.py              # 楼层平面图 + 点击房间查看详情
│   ├── 2_全校能耗趋势.py          # 全校总功率折线图
│   ├── 3_告警记录.py              # 历史告警查询表格
│   └── 4_仿真控制.py              # 启停仿真 / 注入异常
│
└── tests/
    ├── test_simulation/
    ├── test_gateway/
    └── test_storage/
```

### 8.3 核心模块设计

#### 8.3.1 感知层 — VirtualIoTDevice 类设计

```python
class VirtualIoTDevice:
    """单个宿舍虚拟电表设备，运行在独立 asyncio Task 中"""

    def __init__(self, building_id: str, room_id: str, config: DeviceConfig):
        self.device_id = f"MOCK_METER_{building_id}_{room_id}"
        self.topic = f"campus/{building_id}/{room_id}/meter"
        self.state = DeviceState.NORMAL
        self._baseline_power: float
        self._gaussian_noise_std: float
        self._state_machine: StateMachine

    async def run(self, mqtt_client: paho.Client):
        """主循环：按固定频率采集并上报数据"""
        while True:
            metrics = self._generate_metrics()
            payload = self._build_payload(metrics)
            mqtt_client.publish(self.topic, payload)
            await asyncio.sleep(self._report_interval)

    def _generate_metrics(self) -> MetricsSnapshot:
        """基于状态机当前状态生成仿真指标"""
        ...
```

#### 8.3.2 应用层 — 数据流处理管线

```
MQTT Broker (EMQX)
    │
    ▼ (paho-mqtt 后台线程订阅 campus/+/+/meter)
┌──────────────────────────┐
│   mqtt_handler.py        │  ① 反序列化 JSON → MeterReport (Pydantic)
│   on_message() 回调      │  ② 校验数据合法性
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│   rule_engine.py         │  ③ 逐条规则匹配（阈值 / 持续时长）
│   evaluate()             │  ④ 生成 AlertEvent（含级别、触发值）
└──────┬───────┬───────────┘
       │       │
       ▼       ▼
┌─────────┐ ┌──────────────┐
│  Redis  │ │  MySQL       │  ⑤ 双写：更新缓存 + 持久化告警
│  SET    │ │  INSERT      │
└─────────┘ └──────────────┘
       │
       ▼
┌──────────────────────────┐
│  Streamlit Session State │  ⑥ 写入 st.session_state
│  st.fragment 自动刷新    │  ⑦ 页面各区域秒级重绘
└──────────────────────────┘
```

#### 8.3.3 规则引擎详细设计

```python
@dataclass
class Rule:
    name: str
    level: AlertLevel          # CRITICAL / HIGH / MEDIUM
    condition: Callable[[MeterReport], bool]
    message_template: str
    cooldown_seconds: int = 300

RULES: list[Rule] = [
    Rule(
        name="fire_critical",
        level=AlertLevel.CRITICAL,
        condition=lambda r: r.metrics.smoke_density > 0.40 or r.status == "ALARM_FIRE",
        message_template="火灾特级警报：{device_id} 烟雾浓度 {smoke_density}ppm",
        cooldown_seconds=0,
    ),
    Rule(
        name="illegal_appliance",
        level=AlertLevel.HIGH,
        condition=lambda r: r.metrics.current_power > 1500,
        message_template="违章电器：{device_id} 功率 {current_power}W 超限",
        cooldown_seconds=300,
    ),
    Rule(
        name="sustained_overload",
        level=AlertLevel.MEDIUM,
        condition=lambda r: r.metrics.current_power > 800,
        message_template="恶性负载：{device_id} 持续高功率 {current_power}W",
        cooldown_seconds=600,
    ),
]
```

#### 8.3.4 MQTT 后台线程与 Streamlit 集成

```python
import threading
import paho.mqtt.client as mqtt
import streamlit as st

class MQTTBackgroundListener:
    """MQTT 后台守护线程，在 Streamlit 启动时初始化一次"""

    def __init__(self, broker_host: str, broker_port: int):
        self._client = mqtt.Client()
        self._client.on_message = self._on_message
        self._client.connect(broker_host, broker_port)
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()

    def _loop(self):
        self._client.subscribe("campus/+/+/meter")
        self._client.loop_forever()

    def _on_message(self, client, userdata, msg):
        report = MeterReport.model_validate_json(msg.payload)
        alert = rule_engine.evaluate(report)

        redis_cache.set_dorm_status(report)

        # 写入 Streamlit 共享状态
        st.session_state["dorm_data"][report.device_id] = report
        if alert:
            st.session_state["alerts"].append(alert)
            repository.insert_alert(alert)
```

#### 8.3.5 Streamlit 页面实时刷新策略

```python
@st.fragment(run_every="2s")
def dorm_grid_section():
    """宿舍网格拓扑图 — 自动刷新"""
    dorm_data = st.session_state.get("dorm_data", {})
    # 渲染网格：NORMAL=绿，WARNING=黄，ALARM=红
    ...

@st.fragment(run_every="1s")
def alert_panel_section():
    """实时告警滚动面板 — 自动刷新"""
    alerts = st.session_state.get("alerts", [])
    for alert in alerts[-10:]:
        st.error(alert.message) if alert.level == "CRITICAL" else st.warning(alert.message)
```

### 8.4 楼层平面图交互设计

这是系统的核心可视化组件，使用 `st.components.v1.html` 渲染 SVG 楼层平面图。

#### 8.4.1 数据模型

```python
@dataclass
class FloorLayout:
    """楼层布局配置"""
    building_id: str
    floor: int                    # 楼层号
    rooms: list[RoomPosition]     # 房间位置列表

@dataclass
class RoomPosition:
    """单个房间在平面图上的位置与尺寸"""
    room_id: str
    x: int                        # SVG 坐标 x
    y: int                        # SVG 坐标 y
    width: int                    # 房间宽度
    height: int                   # 房间高度
    label: str = ""               # 显示文本，如 "401"
```

#### 8.4.2 交互流程

```
┌─────────────────────────────────────────────────────────────┐
│  侧边栏选择                                                  │
│  [楼栋 ▼]  [楼层 ▼]                                         │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   SVG 楼层平面图                              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐          │
│  │ 401 │ │ 402 │ │ 403 │ │ 404 │ │ 405 │ │ 406 │  ← 走廊   │
│  │ 🟢  │ │ 🟢  │ │ 🟡  │ │ 🟢  │ │ 🔴  │ │ 🟢  │          │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘          │
│            (点击任意房间触发交互)                              │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  房间详情面板（点击后展开）                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 5号楼 402室 — 当前状态：NORMAL                        │   │
│  │  实时功率: 245.3W    电压: 220.1V    烟雾: 0.01ppm   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  今日功率走势（ECharts 动态折线图）                    │   │
│  │  ~~~~~~~~~~~~~~~~~~~~~~~~                            │   │
│  │  00:00  04:00  08:00  12:00  16:00  20:00  24:00    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 8.4.3 SVG 楼层图渲染实现

```python
# src/dormiot/ui/floor_plan.py

import streamlit.components.v1 as components

def render_floor_plan(floor: FloorLayout, dorm_data: dict[str, MeterReport]):
    """
    渲染交互式 SVG 楼层平面图。
    点击房间 → 通过 st.query_params 回传 room_id → Streamlit 重绘详情面板。
    """

    def room_color(room_id: str) -> str:
        report = dorm_data.get(f"MOCK_METER_{floor.building_id}_{room_id}")
        if report is None:
            return "#6b7280"       # 灰色：离线
        match report.status:
            case "ALARM":   return "#ef4444"   # 红色：告警
            case "WARNING": return "#f59e0b"   # 黄色：警告
            case _:         return "#22c55e"   # 绿色：正常

    rooms_svg = ""
    for room in floor.rooms:
        color = room_color(room.room_id)
        rooms_svg += f"""
        <a href="?room={room.room_id}" target="_self">
            <rect x="{room.x}" y="{room.y}"
                  width="{room.width}" height="{room.height}"
                  rx="4" fill="{color}" stroke="#1f2937" stroke-width="1.5"
                  style="cursor:pointer"/>
            <text x="{room.x + room.width/2}" y="{room.y + room.height/2 + 5}"
                  text-anchor="middle" fill="white" font-size="14"
                  font-weight="bold" style="pointer-events:none">
                {room.label}
            </text>
        </a>
        """

    # 添加走廊
    corridor_y = floor.rooms[0].y + floor.rooms[0].height + 10
    corridor_width = max(r.x + r.width for r in floor.rooms) - min(r.x for r in floor.rooms)

    svg_html = f"""
    <div style="display:flex; justify-content:center;">
        <svg width="{corridor_width + 40}" height="160" xmlns="http://www.w3.org/2000/svg">
            <!-- 走廊 -->
            <rect x="10" y="{corridor_y}" width="{corridor_width + 20}" height="20"
                  rx="3" fill="#e5e7eb" stroke="#9ca3af"/>
            <text x="{corridor_width/2 + 20}" y="{corridor_y + 14}"
                  text-anchor="middle" fill="#6b7280" font-size="11">走廊</text>
            <!-- 房间 -->
            {rooms_svg}
        </svg>
    </div>
    """

    components.html(svg_html, height=180)
```

#### 8.4.4 房间详情面板实现

```python
# pages/1_楼层监控.py

import streamlit as st
from dormiot.ui.floor_plan import render_floor_plan
from dormiot.ui.charts import render_power_chart

# 侧边栏：楼栋 + 楼层选择
building_id = st.sidebar.selectbox("选择楼栋", ["5", "6", "12", "13"])
floor = st.sidebar.number_input("选择楼层", min_value=1, max_value=6, value=4)

# 渲染楼层平面图（点击房间会写入 query_params）
floor_layout = get_floor_layout(building_id, floor)
render_floor_plan(floor_layout, st.session_state.get("dorm_data", {}))

# 读取点击的房间
selected_room = st.query_params.get("room")

if selected_room:
    device_id = f"MOCK_METER_{building_id}_{selected_room}"
    report = st.session_state.get("dorm_data", {}).get(device_id)

    st.divider()
    col_info, col_chart = st.columns([1, 2])

    with col_info:
        st.subheader(f"{building_id}号楼 {selected_room}室")
        if report:
            st.metric("实时功率", f"{report.metrics.current_power:.1f} W")
            st.metric("电压", f"{report.metrics.voltage:.1f} V")
            st.metric("烟雾浓度", f"{report.metrics.smoke_density:.2f} ppm")
            st.metric("设备状态", report.status)
        else:
            st.warning("设备离线或无数据")

    with col_chart:
        render_power_chart(device_id)  # ECharts 动态折线图
else:
    st.info("点击平面图上的房间查看实时数据和功率走势")
```

#### 8.4.5 ECharts 图表封装

```python
# src/dormiot/ui/charts.py

from streamlit_echarts import st_echarts

def render_power_chart(device_id: str):
    """渲染指定宿舍的今日功率动态折线图"""
    history = repository.get_power_history(device_id, hours=24)

    option = {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "time",
            "name": "时间",
        },
        "yAxis": {
            "type": "value",
            "name": "功率 (W)",
            "max": 3000,
        },
        "series": [{
            "name": "实时功率",
            "type": "line",
            "smooth": True,
            "data": [[h.timestamp, h.power] for h in history],
            "areaStyle": {"opacity": 0.15},
            "markLine": {
                "data": [
                    {"yAxis": 800,  "name": "恶性负载", "lineStyle": {"color": "#f59e0b"}},
                    {"yAxis": 1500, "name": "违章电器", "lineStyle": {"color": "#ef4444"}},
                ]
            },
        }],
    }

    st_echarts(option, height="350px")

def render_total_power_chart():
    """全校总功率实时折线图"""
    all_data = st.session_state.get("dorm_data", {})
    total_power = sum(r.metrics.current_power for r in all_data.values())

    # 使用 st.session_state 累积历史数据点
    if "total_power_history" not in st.session_state:
        st.session_state["total_power_history"] = []

    from datetime import datetime
    st.session_state["total_power_history"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "power": total_power,
    })
    # 只保留最近 300 个点
    history = st.session_state["total_power_history"][-300:]

    option = {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": [h["time"] for h in history]},
        "yAxis": {"type": "value", "name": "全校总功率 (W)"},
        "series": [{
            "type": "line",
            "smooth": True,
            "data": [h["power"] for h in history],
            "areaStyle": {"opacity": 0.2},
        }],
    }

    st_echarts(option, height="400px")
```

### 8.5 数据库设计

#### 8.5.1 MySQL — 告警日志表

```sql
CREATE TABLE `security_alerts` (
    `id`            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `device_id`     VARCHAR(64)    NOT NULL COMMENT '设备唯一标识',
    `building_id`   VARCHAR(16)    NOT NULL COMMENT '楼栋号',
    `room_id`       VARCHAR(16)    NOT NULL COMMENT '房间号',
    `alert_level`   ENUM('CRITICAL','HIGH','MEDIUM') NOT NULL COMMENT '告警级别',
    `alert_type`    VARCHAR(32)    NOT NULL COMMENT '告警类型码',
    `trigger_value` JSON           NOT NULL COMMENT '触发时的指标快照',
    `message`       VARCHAR(256)   NOT NULL COMMENT '告警描述',
    `resolved`      TINYINT(1)     NOT NULL DEFAULT 0 COMMENT '是否已处理',
    `created_at`    DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `resolved_at`   DATETIME(3)    NULL,

    INDEX `idx_building_room` (`building_id`, `room_id`),
    INDEX `idx_level_created` (`alert_level`, `created_at`),
    INDEX `idx_device_time`   (`device_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='安全告警日志';
```

#### 8.5.2 Redis — 缓存数据结构

```
KEY:   cache:dorm:{building_id}:{room_id}
FIELD: power       → "2150.5"
FIELD: voltage     → "220.4"
FIELD: smoke       → "0.02"
FIELD: status      → "NORMAL"
FIELD: updated_at  → "1716987600"
TTL:   300s

KEY:   cooldown:{device_id}:{rule_name}
VALUE: "1"
TTL:   {cooldown_seconds}s
```

### 8.6 Streamlit 页面设计

| 页面 | 文件 | 功能 |
|------|------|------|
| 概览仪表盘 | `app.py` | 全校宿舍总数、在线设备数、当前告警数、全校总功率折线图 |
| 楼层监控 | `pages/1_楼层监控.py` | **SVG 楼层平面图** — 色块表示房间状态，点击房间展开详情面板 + 功率走势 |
| 全校能耗趋势 | `pages/2_全校能耗趋势.py` | 全校总功率实时折线图 + 各楼栋对比柱状图 |
| 告警记录 | `pages/3_告警记录.py` | 历史告警查询表格，支持级别/时间筛选，标记已处理 |
| 仿真控制 | `pages/4_仿真控制.py` | 启停仿真集群、调整节点数量、向指定设备注入异常 |

### 8.7 配置管理

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DORMIOT_")

    # MQTT
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_topic_pattern: str = "campus/+/+/meter"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MySQL
    mysql_url: str = "mysql+pymysql://root:password@localhost:3306/dormiot"

    # 仿真
    simulation_node_count: int = 50
    simulation_report_interval_ms: int = 1000

    # 规则引擎
    power_threshold_illegal: float = 1500.0
    power_threshold_overload: float = 800.0
    smoke_threshold_critical: float = 0.40
```

### 8.8 部署架构

```yaml
# docker-compose.yml — 仅基础设施，不含应用
services:
  emqx:
    image: emqx/emqx:5.8
    restart: always
    ports: ["1883:1883", "18083:18083"]

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  mysql:
    image: mysql:8.0
    restart: always
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      MYSQL_DATABASE: dormiot
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}

volumes:
  redis_data:
  mysql_data:
```

**网络拓扑**：

```
宿管大屏浏览器 ──HTTP──▶ Streamlit (:8501)  ← uv run 直接运行
                                │
                                ├──MQTT──▶ EMQX (:1883)  ← Docker
                                ├──Redis (:6379)          ← Docker
                                └──MySQL (:3306)          ← Docker
```

### 8.9 性能设计目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 仿真节点并发数 | ≥ 50 | 单进程 asyncio 无阻塞调度 |
| MQTT 消息吞吐 | ≥ 50 msg/s | 50 节点 × 1Hz 采集频率 |
| 规则引擎匹配 | < 5ms / msg | 纯内存阈值比较，无 I/O |
| 页面刷新延迟 | < 3s | `st.fragment(run_every="2s")` 刷新周期 |
| Redis 读写 | < 1ms | 内存级操作 |

### 8.10 开发环境快速启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd DormIoT-Twin

# 2. 安装依赖（uv 自动创建虚拟环境）
uv sync

# 3. 启动基础设施
docker compose up -d

# 4. 初始化数据库表
uv run python -c "from dormiot.storage.models import engine, Base; Base.metadata.create_all(engine)"

# 5. 启动应用
uv run streamlit run app.py
```

---

## 9. 生产环境部署方案（Ubuntu Server）

### 9.1 架构总览

```
                         ┌─────────────────────────────────────────┐
                         │            Ubuntu Server                │
                         │                                         │
  浏览器 ─── HTTP ────▶  │  uv run streamlit run app.py (:8501)    │
                         │                                         │
                         │  Docker（仅基础设施）                    │
                         │    ├── EMQX           (:1883)           │
                         │    ├── Redis          (:6379)           │
                         │    └── MySQL          (:3306)           │
                         └─────────────────────────────────────────┘
```

### 9.2 服务器环境准备

```bash
# ── 1. 系统更新 ──
sudo apt update && sudo apt upgrade -y

# ── 2. 安装 Docker（基础设施用）──
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录终端使 docker 组生效

# ── 3. 安装 uv ──
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# ── 4. 创建项目目录 ──
sudo mkdir -p /opt/dormiot
sudo chown $USER:$USER /opt/dormiot
```

### 9.3 项目部署步骤

```bash
# ── 1. 拉取代码 ──
cd /opt/dormiot
git clone <repo-url> .

# ── 2. 安装依赖 ──
uv sync

# ── 3. 配置环境变量 ──
cp .env.example .env
vim .env
# 修改：
#   MYSQL_ROOT_PASSWORD=你的安全密码
#   DORMIOT_MQTT_BROKER_HOST=localhost
#   DORMIOT_REDIS_URL=redis://localhost:6379/0
#   DORMIOT_MYSQL_URL=mysql+pymysql://root:你的安全密码@localhost:3306/dormiot

# ── 4. 启动基础设施 ──
docker compose up -d

# ── 5. 初始化数据库 ──
uv run python -c "from dormiot.storage.models import engine, Base; Base.metadata.create_all(engine)"

# ── 6. 启动应用 ──
uv run streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

访问 `http://服务器IP:8501` 即可。

### 9.4 Systemd 守护进程（开机自启 + 崩溃重启）

```ini
# /etc/systemd/system/dormiot.service
[Unit]
Description=DormIoT-Twin Streamlit App
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=dormiot
WorkingDirectory=/opt/dormiot
ExecStart=/opt/dormiot/.venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
Restart=always
RestartSec=5
EnvironmentFile=/opt/dormiot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable dormiot   # 开机自启
sudo systemctl start dormiot
sudo systemctl status dormiot   # 确认运行
```

### 9.5 运维常用命令

```bash
# ── 应用管理 ──
sudo systemctl start dormiot      # 启动
sudo systemctl stop dormiot       # 停止
sudo systemctl restart dormiot    # 重启
sudo journalctl -u dormiot -f     # 查看实时日志

# ── 基础设施管理 ──
docker compose ps                  # 查看容器状态
docker compose logs -f emqx        # EMQX 日志
docker compose restart redis       # 重启 Redis

# ── 更新部署 ──
cd /opt/dormiot
git pull
uv sync                           # 更新依赖
sudo systemctl restart dormiot    # 重启应用

# ── 数据库备份 ──
docker compose exec mysql mysqldump -u root -p dormiot > backups/dormiot_$(date +%Y%m%d).sql
```

### 9.6 防火墙配置

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8501/tcp    # Streamlit 直接对外
# 内部服务不暴露：1883 / 3306 / 6379 仅 localhost 访问
sudo ufw enable
```

### 9.7 更新迭代流程

日常开发迭代只需要三步：

```bash
git pull          # 拉取新代码
uv sync           # 同步依赖（如有新增）
sudo systemctl restart dormiot   # 重启生效
```

无需构建前端、无需重新编译、无需 Nginx 配置。
