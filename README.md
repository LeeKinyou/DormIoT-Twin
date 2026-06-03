# DormIoT-Twin — 宿舍安全监控数字孪生系统

基于数字孪生技术的宿舍安全监控系统，通过物理波形合成引擎模拟真实电表数据，MQTT 协议仿真层保留物联网架构语义，AI Agent 智能研判异常，政企科技大屏实时可视化。

## 技术栈

- **Python 3.12+** + **uv** 包管理
- **Streamlit** 全栈 Web 框架
- **Plotly** 数据可视化
- **NumPy** 物理波形合成
- **LangChain + OpenAI** AI 研判
- **Pydantic v2** 数据校验

## 快速启动

### 前置条件

- Python 3.12+
- uv（`pip install uv`）

### 第一步：安装依赖

```bash
uv sync
```

### 第二步：配置 AI（可选）

复制 `.env.example` 为 `.env`，填入 OpenAI 兼容 API 配置：

```
DORMIOT_OPENAI_API_KEY=sk-xxx
DORMIOT_OPENAI_BASE_URL=https://api.openai.com/v1
DORMIOT_OPENAI_MODEL=gpt-4o-mini
```

### 第三步：启动应用

```bash
uv run streamlit run app.py
```

浏览器访问 http://localhost:8501

## 功能说明

### 政企科技大屏

- **顶部状态栏**：系统名称、实时总功率、告警/预警房间数、运行时长
- **房间网格（2×3）**：6 个宿舍卡片，显示功率/电压/烟雾浓度/迷你趋势线
- **实时波形图**：Plotly 绘制，带 800W 预警线和 1500W 告警线，渐变填充
- **MQTT 通信日志**：展示模拟的设备上报消息流

### AI Agent 工作台

- **感知层**：实时监控 6 个房间，1Hz 采样
- **推理层**：波形分类（尖峰/方波/持续高频）→ LLM 智能研判
- **研判输出**：自动触发（功率飙升检测）或手动触发（演示模式）
- **历史记录**：最近 20 条研判结果

### 异常注入（侧边栏）

- 🔥 热得快：瞬间叠加 1800W + 高频毛刺
- 📻 微波炉：方波交替 +1200W / +30W
- 支持清除单个房间或重置所有

## 项目结构

```
DormIoT-Twin/
├── app.py                          # Streamlit 主应用（政企科技大屏）
├── pyproject.toml                  # 项目配置与依赖
├── .env.example                    # 环境变量模板
│
├── src/
│   └── dormiot/
│       ├── config.py               # Pydantic Settings 配置
│       ├── data_store.py           # 内存数据存储 + 后台采集线程
│       ├── ai_diagnoser.py         # AI 波形诊断器（LangChain）
│       │
│       ├── protocol/               # ── MQTT 协议仿真层 ──
│       │   └── mqtt_simulator.py   # 内存 pub/sub Broker
│       │
│       ├── simulation/             # ── 感知层：波形合成 ──
│       │   └── synthesizer.py      # 物理波形合成引擎
│       │
│       ├── schemas/                # ── Pydantic 数据契约 ──
│       │   └── device.py           # MeterReport / DeviceStatus
│       │
│       └── ui/                     # ── UI 辅助函数 ──
│           └── helpers.py          # 颜色/图表/网格数据
│
└── tests/                          # 单元测试（179 个）
    ├── test_protocol/              # MQTT 仿真层测试
    ├── test_simulation/            # 波形合成测试
    ├── test_data_store.py          # 数据存储测试
    ├── test_ai_diagnoser.py        # AI 诊断测试
    └── test_ui_helpers.py          # UI 辅助函数测试
```

## 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 带覆盖率
uv run pytest --cov=dormiot --cov-report=term-missing
```

## 配置说明

通过环境变量或 `.env` 文件配置（前缀 `DORMIOT_`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DORMIOT_OPENAI_API_KEY` | (空) | OpenAI 兼容 API Key |
| `DORMIOT_OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 基础 URL |
| `DORMIOT_OPENAI_MODEL` | `gpt-4o-mini` | 模型名称 |
| `DORMIOT_POWER_THRESHOLD_ILLEGAL` | 1500.0 | 违章电器功率阈值 (W) |
| `DORMIOT_POWER_THRESHOLD_OVERLOAD` | 800.0 | 恶性负载功率阈值 (W) |

## 架构设计

```
┌──────────────────────────────────────────────────────┐
│            感知层：物理波形合成引擎                      │
│   WaveformSynthesizer (NumPy) → 6 个宿舍虚拟电表       │
│   NORMAL / ALARM_RESISTOR / ALARM_MICROWAVE           │
└────────────────────┬─────────────────────────────────┘
                     │ get_next_tick()
                     ▼
┌──────────────────────────────────────────────────────┐
│            网络层：MQTT 协议仿真层                      │
│   MQTTBroker (内存 pub/sub) → Topic 路由               │
│   dormiot/campus/5/{room}/meter                       │
└────────────────────┬─────────────────────────────────┘
                     │ subscribe / publish
                     ▼
┌──────────────────────────────────────────────────────┐
│            应用层：AI Agent + 大屏                      │
│   DataStore (deque) → 功率飙升检测 → AIDiagnoser       │
│   Streamlit 政企科技大屏（科技绿主题）                   │
└──────────────────────────────────────────────────────┘
```

## License

MIT
