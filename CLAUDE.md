# DormIoT-Twin 物联网数字孪生系统

## 已完成：5 阶段核心重构 ✅

原项目包含 MQTT、Redis、MySQL 和多层网关架构。已重构为**纯 Python 单体架构**（Streamlit + 物理特征波形合成算法 + 大模型诊断）。

### 阶段一：架构"断舍离" ✅
- 删除 `docker-compose.yml`、`src/dormiot/gateway/`、`src/dormiot/storage/`
- 移除 `paho-mqtt`, `redis`, `sqlalchemy` 等依赖
- 引入 `numpy`, `langchain`, `langchain-openai`, `plotly`

### 阶段二：物理波形合成引擎 ✅
- `src/dormiot/simulation/synthesizer.py` — WaveformSynthesizer 单例
- NORMAL: 50W + 昼夜节律正弦波 + 高斯噪声
- ALARM_RESISTOR: 基准 + 1800W + 高频毛刺(std=40)
- ALARM_MICROWAVE: 方波交替 +1200W / +30W（每5秒切换）

### 阶段三：内存驱动数据流 ✅
- `src/dormiot/data_store.py` — DataStore(deque) + BackgroundCollector
- 守护线程每秒采集 6 个房间数据，同时发布到 MQTT 仿真层

### 阶段四：政企科技大屏 UI ✅
- 科技绿主色调 `#238E54`
- 深墨绿背景 `#0a1a12`，Inter / Noto Sans SC 字体
- 顶部状态栏 + 房间卡片网格（迷你趋势线）+ Plotly 波形图

### 阶段五：AI 安全专家研判 ✅
- `src/dormiot/ai_diagnoser.py` — AIDiagnoser（LangChain + OpenAI）
- 波形分类：尖峰/方波/持续高频/正常
- 自动触发（功率飙升 1000W/2s）+ 手动演示模式

---

## v2.0 扩展：4 个优化方向 ✅

详见 `docs/PRD_v2.md`

### P1: MQTT 协议仿真层 ✅
- `src/dormiot/protocol/mqtt_simulator.py` — MQTTBroker + MQTTTopic
- 内存 pub/sub，支持 + 和 # 通配符
- BackgroundCollector 每次采集自动发布到 Broker

### P2: 政企科技大屏 UI ✅
- 科技绿主题配色体系（背景/卡片/主色/状态/文字 5 层）
- 顶部状态栏（总功率/告警数/预警数/运行时长）
- 房间卡片（功率数字 + 迷你趋势线 + 电压/烟雾 + 状态条）
- Plotly 波形图（科技绿线条 + 渐变填充 + 阈值参考线）
- MQTT 通信日志面板

### P3: AI Agent 独立展示 ✅
- AI Agent 工作台面板（感知层/推理层/研判输出）
- 推理链路可视化（波形分类 → Prompt → LLM）
- 演示模式（侧边栏手动触发）+ 自动模式
- 研判历史记录（最近 20 条）

### P4: 文档同步更新 ✅
- `README.md` — 更新文件结构和架构说明
- `docs/Development-Plan.md` — 更新为 v2.0 架构
- `docs/PRD_v2.md` — v2.0 产品需求文档

---

## 测试

```bash
uv run pytest tests/ -v          # 179 个测试
uv run pytest --cov=dormiot      # 带覆盖率
```

## 启动

```bash
uv sync
uv run streamlit run app.py
```
