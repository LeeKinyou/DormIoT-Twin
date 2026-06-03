# DormIoT-Twin 敏捷开发全流程规划

> 基于 Scrum 框架 · 1 周 Sprint · 迭代交付
> 更新日期：2026-06-03（v2.0 架构）

---

## 1. 项目架构（v2.0）

v2.0 架构采用纯 Python 单体方案，无需外部中间件：

- **感知层**：物理波形合成引擎（NumPy），替代真实硬件和简单随机数
- **网络层**：MQTT 协议仿真层（内存 pub/sub），保留物联网协议语义
- **应用层**：Streamlit 政企科技大屏 + AI Agent 智能研判
- **数据层**：内存 deque 队列（60 秒历史），无外部数据库

### 技术栈

| 层级 | 技术 |
|------|------|
| 感知层 | NumPy 波形合成、昼夜节律正弦波、方波/毛刺模拟 |
| 网络层 | 内存 MQTT Broker（支持 +/# 通配符） |
| 应用层 | Streamlit、Plotly、LangChain + OpenAI |
| 包管理 | uv |

---

## 2. 已完成 Sprint

### Sprint 1-5：核心重构 ✅（2026-06-03 完成）

| 阶段 | 内容 | 测试数 |
|------|------|--------|
| 阶段一 | 架构断舍离（删除 MQTT/Redis/MySQL） | 63 |
| 阶段二 | 物理波形合成引擎 | 81 |
| 阶段三 | 内存驱动数据流 | 101 |
| 阶段四 | 政企科技大屏 UI | 121 |
| 阶段五 | AI 安全专家研判模块 | 135 |

### Sprint 6：v2.0 扩展 ✅（2026-06-03 完成）

| 内容 | 测试数 |
|------|--------|
| P1: MQTT 协议仿真层 | 155 |
| P2: 政企科技大屏 UI 重构（科技绿主题） | 175 |
| P3: AI Agent 独立展示工作台 | 175 |
| P4: 文档同步更新 | 179 |

---

## 3. v2.0 功能清单

### P1: MQTT 协议仿真层 ✅

- [x] `src/dormiot/protocol/mqtt_simulator.py` — MQTTBroker + MQTTTopic
- [x] 内存 pub/sub，支持 + 和 # 通配符
- [x] 消息日志（最近 100 条）
- [x] 集成到 BackgroundCollector（每次采集自动发布）
- [x] 20 个单元测试

### P2: 政企科技大屏 UI ✅

- [x] 科技绿主色调 `#238E54`
- [x] 深墨绿背景 `#0a1a12`
- [x] Inter / Noto Sans SC 无衬线字体
- [x] 顶部状态栏（总功率/告警数/运行时长）
- [x] 房间卡片（功率/电压/烟雾/迷你趋势线）
- [x] 卡片顶部状态条（绿/黄/红）+ 告警脉冲动画
- [x] Plotly 波形图（科技绿线条 + 渐变填充 + 阈值参考线）
- [x] MQTT 通信日志面板
- [x] 41 个 UI 辅助函数测试

### P3: AI Agent 独立展示 ✅

- [x] AI Agent 工作台面板（感知层/推理层/研判输出）
- [x] 推理链路可视化（波形分类 → Prompt 构建 → LLM 研判）
- [x] 演示模式（侧边栏手动触发 AI 研判）
- [x] 自动模式（功率飙升 1000W/2s 自动触发）
- [x] 研判历史记录（最近 20 条）
- [x] 16 个 AI 诊断器测试

### P4: 文档同步更新 ✅

- [x] `README.md` — 更新文件结构、依赖、架构说明
- [x] `docs/Development-Plan.md` — 更新为 v2.0 架构
- [x] `docs/PRD.md` — 保留作为历史参考
- [x] `docs/PRD_v2.md` — v2.0 产品需求文档

---

## 4. 用户故事验收标准

| ID | 故事 | 验收标准 | 状态 |
|----|------|---------|------|
| US-001 | MQTT 仿真层 | Broker 单例、Topic 通配符、消息日志、回调通知 | ✅ |
| US-002 | 政企风 UI | 科技绿主题、状态栏、卡片网格、波形图、无赛博朋克元素 | ✅ |
| US-003 | AI Agent 工作台 | 感知→推理→研判全链路、演示模式、历史记录 | ✅ |
| US-004 | MQTT 通信日志 | 侧边栏/底部显示实时 MQTT 消息流 | ✅ |
| US-005 | 房间卡片增强 | 迷你趋势线、电压/烟雾辅助信息、hover 效果 | ✅ |
| US-006 | 波形图优化 | 真实时间轴、阈值参考线、科技绿渐变填充 | ✅ |

---

## 5. 测试策略

### 测试金字塔

```
         ┌──────────┐
         │  集成测试   │  ← BackgroundCollector + MQTT
         │  (5-10 个) │
         ├──────────┤
         │  单元测试    │  ← 每个模块独立测试
         │ (170+ 个)  │
         └──────────┘
```

### 测试运行

```bash
# 全部测试
uv run pytest tests/ -v

# 带覆盖率
uv run pytest --cov=dormiot --cov-report=term-missing

# 单模块
uv run pytest tests/test_protocol/ -v      # MQTT 仿真
uv run pytest tests/test_simulation/ -v    # 波形合成
uv run pytest tests/test_data_store.py -v  # 数据存储
uv run pytest tests/test_ai_diagnoser.py -v # AI 诊断
uv run pytest tests/test_ui_helpers.py -v  # UI 辅助
```

---

## 6. 部署

纯 Python 单体应用，无需 Docker：

```bash
uv sync
uv run streamlit run app.py
```

生产部署：

```bash
uv run streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

---

## 7. 里程碑

```
Sprint 1-5 (已完成)          Sprint 6 (已完成)
┌──────────────────┐        ┌──────────────────┐
│ 核心重构          │   ──▶  │ v2.0 扩展         │
│ 5 阶段 TDD       │        │ MQTT+UI+AI+文档   │
│ 135 测试          │        │ 179 测试          │
└──────────────────┘        └──────────────────┘
```
