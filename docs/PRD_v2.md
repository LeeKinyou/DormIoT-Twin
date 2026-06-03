# DormIoT-Twin v2.0 产品需求文档（PRD）

> **文档版本**：v2.0  
> **更新日期**：2026-06-03  
> **状态**：待评审

---

## 一、现状诊断：三个致命问题

### 问题 1：MQTT 被彻底删除，"物联网"名存实亡

**现状**：重构阶段一将 MQTT、Redis、MySQL 全部清除，项目变成了一个纯粹的"Python 数值模拟器 + Streamlit 看板"。虽然功能上确实不再需要外部中间件，但从课程设计展示的角度看：

- 没有 MQTT 协议 → 无法展示"感知层 → 网络层 → 应用层"的经典物联网三层架构
- 没有 Topic 订阅/发布 → 无法演示设备上报、云端下发的通信过程
- 没有 Broker → 答辩时无法回答"你的数据是怎么从设备到服务器的"

**结论**：MQTT 不能作为运行时依赖，但必须作为**协议仿真层**保留在架构中，用于演示和教学。

### 问题 2：UI 是"赛博朋克风"，而非"政企科技大屏"

**现状**（`app.py` 第 29-113 行 CYBERPUNK_CSS）：

- 背景色 `#0a0a0f`（纯黑偏紫）—— 过于暗沉，不适合投影展示
- 霓虹绿 `#00ff41` + 霓虹红 `#ff073a` —— 赛博朋克游戏风，不是政企风
- `Courier New` 等宽字体全局使用 —— 像终端黑客界面，不像监控中心
- 房间卡片只有功率数字和状态文字 —— 信息密度低，视觉层次差
- 告警日志是简单的 `border-left` 列表 —— 没有时间轴感，没有优先级区分
- 波形图使用 Plotly 默认暗色主题 —— 与整体风格不统一，渐变填充色不协调

**用户期望**：简约清爽的政企科技可视化大屏，以科技绿色（`#238E54`）为主色调，体现科技感与专业性。

### 问题 3：AI Agent 模块"藏得太深"

**现状**：

- `ai_diagnoser.py` 存在且功能完整（波形分类 + LLM 研判），但 UI 上完全没有突出
- 触发条件苛刻：需要 2 秒内功率飙升 1000W 才触发，正常使用时几乎看不到
- 展示位置隐蔽：告警日志在页面中部，被房间卡片和波形图淹没
- 没有"AI Agent"的概念包装：只是叫"AI 安全研判日志"，缺乏 Agent 的自主感知→分析→决策→执行闭环展示

**用户期望**：AI Agent 应该是系统的"杀手锏"，需要独立的展示区域，有完整的感知→推理→输出链路可视化。

---

## 二、修改方案总览

| 序号 | 修改方向 | 核心改动 | 优先级 |
|------|---------|---------|--------|
| P1 | MQTT 协议仿真层 | 保留 MQTT Topic 设计，用内存 pub/sub 模拟 Broker | ⭐⭐⭐ |
| P2 | 政企科技大屏 UI | 全新视觉体系：科技绿主色调（`#238E54`）、卡片化布局、专业图表 | ⭐⭐⭐ |
| P3 | AI Agent 独立展示 | 增加 Agent 工作台面板，展示感知→推理→研判全链路 | ⭐⭐⭐ |
| P4 | 文档同步更新 | PRD.md / README.md / Development-Plan.md 与代码对齐 | ⭐⭐ |

---

## 三、P1：MQTT 协议仿真层（保留物联网门面）

### 3.1 设计理念

**不做真正的 MQTT Broker**，而是在代码中保留 MQTT 的协议语义和 Topic 设计，用内存中的发布/订阅模式模拟 MQTT 通信过程。这样：

- 代码中可以看到 `dormiot/campus/5/101/meter` 这样的 Topic 结构
- 可以演示"设备发布 → Broker 路由 → 应用层订阅"的数据流
- 答辩时可以说"我们用内存队列模拟了 MQTT Broker，在生产环境中替换为 EMQX 即可"

### 3.2 具体实现

**新建 `src/dormiot/protocol/mqtt_simulator.py`**：

```python
"""MQTT 协议仿真层 —— 内存 pub/sub 模拟 Broker"""
from __future__ import annotations
import threading
from collections import defaultdict
from typing import Callable, Any

class MQTTTopic:
    """MQTT Topic 常量定义（标准宿舍物联网 Topic 设计）"""
    # 设备上报
    METER_REPORT = "dormiot/campus/{building}/{room}/meter"      # 电表数据
    SMOKE_REPORT = "dormiot/campus/{building}/{room}/smoke"      # 烟雾传感器
    DEVICE_STATUS = "dormiot/campus/{building}/{room}/status"    # 设备状态
    
    # 云端下发
    COMMAND = "dormiot/campus/{building}/{room}/command"          # 控制指令
    ALARM = "dormiot/alarm/{building}/{room}"                     # 告警推送
    
    # 系统级
    SYSTEM_HEARTBEAT = "dormiot/system/heartbeat"                 # 心跳
    SYSTEM_BROADCAST = "dormiot/system/broadcast"                 # 广播

class MQTTBroker:
    """内存 MQTT Broker（单例）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers = defaultdict(list)
                cls._instance._message_log = []  # 最近 N 条消息日志
            return cls._instance
    
    def publish(self, topic: str, payload: dict, qos: int = 0) -> None:
        """模拟 MQTT 发布"""
        message = {"topic": topic, "payload": payload, "qos": qos}
        self._message_log.append(message)
        if len(self._message_log) > 100:
            self._message_log.pop(0)
        
        # 通知订阅者
        for pattern, callbacks in self._subscribers.items():
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    callback(topic, payload)
    
    def subscribe(self, topic_pattern: str, callback: Callable) -> None:
        """模拟 MQTT 订阅"""
        self._subscribers[topic_pattern].append(callback)
    
    def get_recent_messages(self, limit: int = 20) -> list[dict]:
        """获取最近的消息日志（用于 UI 展示）"""
        return self._message_log[-limit:]
    
    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """Topic 匹配（支持 + 和 # 通配符）"""
        # 简化实现：精确匹配或 # 通配
        if pattern.endswith("#"):
            return topic.startswith(pattern[:-2])
        return topic == pattern
```

**修改 `src/dormiot/data_store.py`**：

在 `BackgroundCollector` 中，每次采集数据时同时发布到 MQTT Broker：

```python
def _collect_loop(self):
    """后台采集循环"""
    broker = MQTTBroker()
    while self._running:
        tick = self._synth.get_next_tick()
        self._store.push_tick(tick)
        
        # 模拟设备通过 MQTT 上报数据
        for room_id, data in tick.items():
            topic = MQTTTopic.METER_REPORT.format(building="5", room=room_id)
            broker.publish(topic, {
                "device_id": f"MOCK_METER_BLDG5_RM{room_id}",
                "power": data["power"],
                "voltage": data["voltage"],
                "timestamp": time.time()
            })
        
        time.sleep(self._interval)
```

### 3.3 UI 展示：MQTT 通信日志面板

在侧边栏或页面底部增加"MQTT 通信日志"面板：

```
┌─────────────────────────────────────────────┐
│  📡 MQTT 通信日志                            │
├─────────────────────────────────────────────┤
│  14:32:01  → dormiot/campus/5/101/meter     │
│             {"power": 52.3, "voltage": 220} │
│  14:32:01  → dormiot/campus/5/102/meter     │
│             {"power": 1847.2, ...}          │
│  14:32:00  ⚠ dormiot/alarm/5/102           │
│             {"type": "power_spike"}         │
└─────────────────────────────────────────────┘
```

---

## 四、P2：政企科技大屏 UI 重构

### 4.1 视觉设计规范

**摒弃赛博朋克，采用"科技绿"政企科技风**：

> 主色调取自高校标准色 `#238E54`（RGB: 35, 142, 84），体现科技感与专业性。

| 元素 | 当前值 | 新值 | 说明 |
|------|--------|------|------|
| 主背景 | `#0a0a0f`（纯黑紫） | `#0a1a12`（深墨绿） | 深绿底色，沉稳专业 |
| 卡片背景 | `#111118` | `#132a1e`（暗绿灰） | 带绿调的深色卡片 |
| 侧边栏背景 | `#0d0d14` | `#0d1f16` | 比主背景略浅 |
| 边框色 | `#1a1a2e` | `#1e3a2a`（墨绿边框） | 柔和的绿灰边框 |
| 主色调（正常） | `#00ff41`（霓虹绿） | `#238E54`（科技绿） | 标准色 |
| 主色调（强调） | - | `#2ca86a`（亮翠绿） | hover/选中状态 |
| 告警色 | `#ff073a`（霓虹红） | `#e74c3c`（柔和红） | 降低刺眼感，暖红调 |
| 警告色 | - | `#f39c12`（琥珀黄） | 预警状态 |
| 成功色 | `#00ff41` | `#27ae60`（翡翠绿） | 更自然的绿色 |
| 正文字色 | `#e0e0e0` | `#d4e6df`（薄荷白） | 带绿调的浅灰 |
| 辅助字色 | `#666` | `#7f9a8e`（绿灰） | 绿灰色辅助色 |
| 字体 | `Courier New`（等宽） | `Inter` / `Noto Sans SC` | 专业无衬线 |

**色彩体系示意**：

```
背景层:   #0a1a12 ──→ #0d1f16 ──→ #132a1e
          (主背景)     (侧边栏)     (卡片)

主色层:   #238E54 ──→ #2ca86a ──→ #34c77b
          (科技绿)     (亮翠绿)     (高亮绿)

状态层:   #27ae60 ──→ #f39c12 ──→ #e74c3c
          (正常/成功)   (预警)       (告警)

文字层:   #d4e6df ──→ #7f9a8e
          (主文字)      (辅助文字)
```

**色彩使用规范**：

| 场景 | 颜色 | 色值 | 用途 |
|------|------|------|------|
| 主背景 | 深墨绿 | `#0a1a12` | 页面整体背景 |
| 卡片背景 | 暗绿灰 | `#132a1e` | 房间卡片、面板背景 |
| 边框 | 墨绿边框 | `#1e3a2a` | 卡片、分隔线 |
| 正常状态 | 科技绿 | `#238E54` | 主色调、正常指示、统计数字 |
| 强调/hover | 亮翠绿 | `#2ca86a` | 悬停状态、选中状态、链接 |
| 高亮 | 高亮绿 | `#34c77b` | 特殊强调、进度条 |
| 成功 | 翡翠绿 | `#27ae60` | 成功消息、正常状态指示 |
| 预警 | 琥珀黄 | `#f39c12` | 预警状态、警告提示 |
| 告警 | 柔和红 | `#e74c3c` | 告警状态、错误提示、异常指示 |
| 主文字 | 薄荷白 | `#d4e6df` | 正文、标题 |
| 辅助文字 | 绿灰 | `#7f9a8e` | 说明文字、次要信息 |

### 4.2 页面布局重构

**当前布局**（线性堆砌）：
```
标题
告警日志
房间卡片（6宫格）
波形图
```

**新布局**（大屏风格）：
```
┌──────────────────────────────────────────────────────────┐
│  顶部状态栏：系统名称 | 运行时长 | 总功率 | 告警数 | 时间  │
├────────────────────────────┬─────────────────────────────┤
│                            │                             │
│   左侧：AI Agent 工作台     │   右侧：宿舍空间拓扑        │
│   - 感知状态                │   - 6宫格房间卡片           │
│   - 推理链路                │   - 每个卡片含：            │
│   - 研判输出                │     房间号/功率/状态/趋势   │
│                            │                             │
├────────────────────────────┴─────────────────────────────┤
│                                                          │
│   底部：实时波形监控区                                     │
│   - 全校总功率趋势图                                      │
│   - 选中房间详细波形（带阈值线）                           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│   底栏：MQTT 通信日志 | 系统事件时间轴                     │
└──────────────────────────────────────────────────────────┘
```

### 4.3 顶部状态栏设计

```html
<!-- 参考海康威视/华为云 IoT 大屏顶部状态栏，科技绿主色调 -->
<div class="top-bar">
    <div class="logo-area">
        <span class="system-icon">🏠</span>
        <span class="system-name">DormIoT-Twin 宿舍安全监控数字孪生</span>
    </div>
    <div class="stats-area">
        <div class="stat-item">
            <span class="stat-value" id="total-power">324W</span>
            <span class="stat-label">实时总功率</span>
        </div>
        <div class="stat-item">
            <span class="stat-value alarm" id="alarm-count">1</span>
            <span class="stat-label">异常房间</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">12:34:56</span>
            <span class="stat-label">运行时长</span>
        </div>
    </div>
</div>
```

### 4.4 房间卡片重新设计

**当前卡片**：只有房间号、功率数字、状态文字

**新卡片设计**：

```
┌─────────────────────────────────┐
│  ▲ 顶部状态指示条（绿/红）        │
├─────────────────────────────────┤
│  ROOM 101          ● 正常       │
│                                 │
│     52.3 W                     │
│     ──────── (迷你趋势线)        │
│                                 │
│  220V  │  烟雾: 0.01ppm        │
└─────────────────────────────────┘
```

关键改进：
- 增加迷你趋势线（sparkline），一目了然看到功率变化趋势
- 电压和烟雾密度作为辅助信息展示
- 卡片顶部状态条：正常时科技绿（`#238E54`）渐变，告警时红色脉冲
- 圆角 + 微阴影，增加层次感
- hover 时边框变为亮翠绿（`#2ca86a`）

### 4.5 波形图优化

**当前问题**：
- Plotly 默认暗色主题与整体风格不协调
- 渐变填充色 (`rgba(0, 212, 255, 0.1)`) 太淡，看不清
- X 轴标签 `T-60`, `T-59`... 不直观

**优化方案**：
- 统一图表背景色与页面背景色一致（`#0a1a12`）
- 波形线条使用科技绿（`#238E54`）
- 渐变填充色：`rgba(35, 142, 84, 0.3)`（科技绿半透明）
- X 轴显示真实时间戳（`14:32:01`），而非相对时间
- 增加 800W（预警阈值，琥珀黄 `#f39c12`）和 1500W（告警阈值，柔和红 `#e74c3c`）水平参考线
- 增加图例，区分不同房间的颜色

### 4.6 CSS 实现示例

```css
/* 政企科技风 —— 科技绿主题 */
.stApp {
    background: linear-gradient(180deg, #0a1a12 0%, #081510 100%);
    color: #d4e6df;
}

section[data-testid="stSidebar"] {
    background: #0d1f16;
    border-right: 1px solid #1e3a2a;
}

/* 顶部状态栏 */
.top-status-bar {
    background: linear-gradient(90deg, #132a1e 0%, #0a1a12 100%);
    border-bottom: 1px solid #1e3a2a;
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* 房间卡片 */
.room-card {
    background: #132a1e;
    border: 1px solid #1e3a2a;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}

.room-card:hover {
    border-color: #2ca86a;
    box-shadow: 0 4px 20px rgba(44, 168, 106, 0.2);
}

.room-card.normal {
    border-top: 3px solid #238E54;
}

.room-card.alarm {
    border-top: 3px solid #e74c3c;
    animation: alarm-pulse 2s ease-in-out infinite;
}

@keyframes alarm-pulse {
    0%, 100% { border-top-color: #e74c3c; }
    50% { border-top-color: #ff8a80; }
}

/* 告警条 */
.alert-entry {
    background: #132a1e;
    border-left: 3px solid #e74c3c;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
}

/* 统计数字 */
.stat-value {
    font-size: 28px;
    font-weight: 600;
    color: #238E54;
    font-variant-numeric: tabular-nums;
}

.stat-value.alarm {
    color: #e74c3c;
}

.stat-value.warning {
    color: #f39c12;
}

/* 主色调强调元素 */
.highlight {
    color: #2ca86a;
}

/* 成功状态 */
.success {
    color: #27ae60;
}

/* 预警状态 */
.warning {
    color: #f39c12;
}
```

---

## 五、P3：AI Agent 独立展示模块

### 5.1 问题分析

当前 AI 模块（`ai_diagnoser.py`）的调用链路是：

```
功率飙升检测 → 波形分类 → 构建 Prompt → 调用 LLM → 显示结果
```

**问题**：
1. 触发条件太苛刻（2 秒内飙升 1000W），正常使用时看不到
2. 没有展示 AI 的"思考过程"，只展示最终结果
3. 没有 Agent 的概念包装，只是一个函数调用

### 5.2 AI Agent 工作台设计

在页面左侧增加独立的"AI Agent 工作台"面板，展示完整的感知→推理→输出链路：

```
┌─────────────────────────────────────┐
│  🤖 AI 安全专家 Agent               │
│  状态: 🟢 运行中 | 已研判: 12 次    │
├─────────────────────────────────────┤
│                                     │
│  【感知层】                          │
│  ├─ 监控房间: 101-106 (6间)         │
│  ├─ 采样频率: 1Hz                   │
│  ├─ 当前功率: 324W (全校)           │
│  └─ 异常检测: 1000W/2s 阈值        │
│                                     │
│  【推理层】                          │
│  ├─ 波形分类器: 统计特征分析        │
│  │   - 尖峰检测 ✓                   │
│  │   - 方波检测 ✓                   │
│  │   - 持续高频检测 ✓               │
│  └─ LLM 分析: DeepSeek-V4-Flash    │
│                                     │
│  【最新研判】                        │
│  ├─ 时间: 14:32:15                  │
│  ├─ 房间: 102                       │
│  ├─ 波形: 尖峰型 (52W → 1847W)     │
│  └─ 结论: 疑似热得快/吹风机启动，   │
│          建议立即检查该宿舍          │
│                                     │
│  【历史研判】 (可展开)               │
│  ├─ 14:30:22 Room 103 方波型       │
│  └─ 14:28:11 Room 101 持续高频     │
│                                     │
└─────────────────────────────────────┘
```

### 5.3 降低触发门槛，增加演示性

**当前触发条件**：2 秒内飙升 1000W → 太苛刻

**新增两种触发模式**：

1. **自动模式**（保持原有逻辑）：功率飙升时自动触发
2. **演示模式**（新增）：侧边栏增加"AI 分析"按钮，手动选择房间触发 AI 研判，用于答辩演示

```python
# 侧边栏新增
st.sidebar.markdown("### 🤖 AI Agent 演示")
demo_room = st.sidebar.selectbox("选择房间", ["101", "102", "103", "104", "105", "106"])
if st.sidebar.button("🔬 触发 AI 研判"):
    power_array = store.get_power_array(demo_room)
    # 展示完整的推理链路
    waveform_type = diagnoser.classify_waveform(power_array)
    prompt = diagnoser.build_prompt(power_array, demo_room)
    result = diagnoser._call_llm(prompt)
    # 将推理过程写入 Agent 工作台
```

### 5.4 推理链路可视化

在 AI Agent 工作台中，展示从数据到结论的完整链路：

```
原始波形数据 → 特征提取 → 波形分类 → Prompt 构建 → LLM 推理 → 研判输出

[52.3, 51.8, 1847.2, 1852.1, ...] 
    ↓
统计特征: avg=358.2, max=1852.1, min=51.8, range=1800.3
    ↓
分类结果: 尖峰型 (前3点<200W, 后3点>1000W, 范围>800W)
    ↓
Prompt: "你是一个物联网数字孪生安防专家..."
    ↓
LLM (DeepSeek-V4-Flash): "疑似热得快启动..."
    ↓
研判结论: "房间102疑似使用热得快，功率从52W瞬间飙升至1847W，建议立即检查"
```

### 5.5 Agent 状态持久化

将 AI 研判历史保存到 session state 中，支持：

- 最近 20 条研判记录
- 按房间筛选
- 按时间排序
- 导出研判报告（可选）

---

## 六、P4：文档同步更新

### 6.1 需要更新的文档

| 文档 | 当前状态 | 更新内容 |
|------|---------|---------|
| `docs/PRD.md` | 描述重构前架构（MQTT/Redis/MySQL） | 重写为 v2.0 架构 |
| `docs/Development-Plan.md` | Sprint 3/4 涉及已删除模块 | 更新为当前架构的开发计划 |
| `README.md` | 包含已删除文件和旧依赖 | 同步更新文件结构和依赖说明 |
| `CLAUDE.md` | 5 阶段重构指导 | 保留历史，新增 v2.0 扩展阶段 |

### 6.2 README.md 更新要点

**删除**：
- `docker-compose.yml` 相关说明
- `publisher.py`, `mqtt_handler.py`, `redis_cache.py`, `models.py` 等已删除文件
- MQTT/Redis/MySQL 环境变量配置

**新增**：
- v2.0 架构说明（MQTT 仿真层 + 政企风 UI + AI Agent）
- 项目截图（新 UI）
- AI Agent 功能演示说明

---

## 七、实施路线图

### Phase 1：MQTT 协议仿真层（1-2 天）

- [ ] 新建 `src/dormiot/protocol/mqtt_simulator.py`
- [ ] 定义标准 MQTT Topic 常量
- [ ] 实现内存 pub/sub Broker
- [ ] 在 `BackgroundCollector` 中集成 MQTT 发布
- [ ] 新增 MQTT 通信日志 UI 面板

### Phase 2：政企科技大屏 UI（2-3 天）

- [ ] 重新设计色彩体系（科技绿主题 `#238E54`）
- [ ] 重构页面布局（顶部状态栏 + 左右分栏 + 底部图表）
- [ ] 重新设计房间卡片（迷你趋势线 + 更多指标）
- [ ] 优化波形图（时间轴 + 阈值线 + 渐变填充）
- [ ] 增加顶部状态栏（总功率/告警数/运行时长）

### Phase 3：AI Agent 工作台（1-2 天）

- [ ] 新增 AI Agent 工作台 UI 面板
- [ ] 展示感知→推理→研判全链路
- [ ] 增加手动触发 AI 研判的演示模式
- [ ] 推理过程可视化（特征提取 → 分类 → Prompt → LLM）
- [ ] 研判历史记录与筛选

### Phase 4：文档更新（1 天）

- [ ] 重写 `docs/PRD.md` 为 v2.0
- [ ] 更新 `README.md`
- [ ] 更新 `docs/Development-Plan.md`
- [ ] 更新 `CLAUDE.md` 增加 v2.0 扩展阶段

---

## 八、技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| LLM API 调用失败 | AI 研判功能不可用 | 增加本地规则引擎兜底（power > 1500W → 自动告警） |
| Streamlit 性能瓶颈 | 大屏刷新卡顿 | 减少不必要的 `st.rerun()`，使用 `st.empty()` 局部更新 |
| MQTT 仿真层增加复杂度 | 代码量增加 | 保持仿真层独立，不影响核心数据流 |
| 政企风 UI 开发量大 | 周期延长 | 优先改造核心区域（状态栏 + 卡片 + 波形图），其他区域渐进优化 |

---

## 九、验收标准

### 功能验收

- [ ] MQTT 通信日志面板正常显示设备上报消息
- [ ] 6 个房间卡片正常显示功率、电压、烟雾密度、趋势线
- [ ] 功率 > 1500W 时卡片变红并脉冲告警
- [ ] AI Agent 工作台显示完整的感知→推理→研判链路
- [ ] 手动触发 AI 研判功能正常
- [ ] 波形图实时更新，带阈值参考线

### 视觉验收

- [ ] 整体色调为科技绿（`#238E54`）为主，无赛博朋克元素
- [ ] 字体为无衬线字体（Inter / Noto Sans SC）
- [ ] 卡片有圆角、阴影、hover 效果，正常状态顶部绿色边框
- [ ] 告警色使用柔和红（`#e74c3c`），不刺眼
- [ ] 预警色使用琥珀黄（`#f39c12`）
- [ ] 背景色为深墨绿（`#0a1a12`），沉稳专业
- [ ] 在 1920x1080 分辨率下显示正常
- [ ] 整体配色体现高校科技感

### 文档验收

- [ ] PRD.md 与代码架构一致
- [ ] README.md 无已删除文件的引用
- [ ] 所有环境变量配置说明与 `.env.example` 一致
