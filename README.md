# DormIoT-Twin — 宿舍物联网安全监控数字孪生系统

基于数字孪生技术的宿舍安全监控系统，通过虚拟仿真设备模拟真实电表数据，实时监测功率异常和烟雾浓度，自动触发告警并可视化展示。

## 技术栈

- **Python 3.12+** + **uv** 包管理
- **Streamlit** 全栈 Web 框架
- **paho-mqtt** MQTT 通信
- **Redis** 设备状态缓存
- **MySQL** 告警持久化
- **Pydantic v2** 数据校验
- **ECharts** 数据可视化

## 快速启动（三步部署）

### 前置条件

- Python 3.12+
- Docker & Docker Compose
- uv（`pip install uv`）

### 第一步：安装依赖

```bash
uv sync
```

### 第二步：启动基础设施

```bash
docker compose up -d
```

启动 EMQX（MQTT Broker）、Redis、MySQL 三个服务。

验证服务状态：
```bash
docker compose ps
```

三个服务应显示 `healthy` 状态。

### 第三步：启动应用

```bash
uv run streamlit run app.py
```

浏览器访问 http://localhost:8501

## 功能说明

### 实时监控（Tab 1）

- **概览仪表盘**：在线设备数、正常/预警/告警设备数、全校总功率
- **全校功率趋势图**：实时折线图，含 800W（恶性负载）和 1500W（违章电器）阈值线
- **设备状态饼图**：正常/预警/告警设备分布
- **楼层平面图**：SVG 渲染，颜色映射（绿=正常/黄=预警/红=告警/灰=离线），点击房间查看详情
- **房间详情面板**：单房间指标 + 功率走势折线图

数据每 2 秒自动刷新。

### 告警记录（Tab 2）

- 表格展示告警列表
- 支持按级别（CRITICAL/HIGH/MEDIUM）、楼栋、处理状态筛选
- 可标记告警为已处理

### 仿真控制（Tab 3）

- 启停仿真集群
- 手动发送一轮数据
- 向指定设备注入异常状态（WARNING/ALARM）
- 重置所有设备为 NORMAL
- 查看所有设备状态一览

## 项目结构

```
DormIoT-Twin/
├── app.py                          # Streamlit 主应用入口
├── docker-compose.yml              # 基础设施编排（EMQX/Redis/MySQL）
├── pyproject.toml                  # 项目配置与依赖
├── src/
│   └── dormiot/
│       ├── config.py               # Pydantic Settings 配置管理
│       ├── schemas/
│       │   ├── device.py           # MeterReport / MetricsSnapshot 数据契约
│       │   └── alert.py            # AlertEvent 告警事件模型
│       ├── simulation/
│       │   ├── noise.py            # 高斯噪声生成
│       │   ├── state_machine.py    # 设备状态机
│       │   ├── device.py           # VirtualIoTDevice 虚拟设备
│       │   ├── cluster.py          # SimulationCluster 集群编排
│       │   └── publisher.py        # MQTTPublisher 发布客户端
│       ├── gateway/
│       │   ├── mqtt_handler.py     # MQTT 后台监听器
│       │   ├── rule_engine.py      # 规则引擎（异常检测）
│       │   └── pipeline.py         # 数据管线串联
│       ├── storage/
│       │   ├── redis_cache.py      # Redis 缓存封装
│       │   ├── models.py           # SQLAlchemy ORM 模型
│       │   └── repository.py       # 告警 CRUD
│       └── ui/
│           ├── floor_plan.py       # SVG 楼层平面图
│           └── charts.py           # ECharts 图表配置
└── tests/
    ├── test_schemas/               # Schema 单元测试
    ├── test_simulation/            # 仿真层单元测试
    ├── test_gateway/               # 网关层测试（规则引擎 + MQTT 集成）
    └── test_storage/               # 存储层集成测试
```

## 运行测试

```bash
# 运行所有单元测试（无需外部服务）
uv run pytest tests/ -v

# 仅运行规则引擎测试
uv run pytest tests/test_gateway/test_rule_engine.py -v

# 运行集成测试（需要 docker compose up -d）
uv run pytest tests/test_gateway/test_mqtt.py -v
uv run pytest tests/test_storage/ -v
```

## 配置说明

通过环境变量或 `.env` 文件配置（前缀 `DORMIOT_`）。密码中的特殊字符（如 `@` `:` `/`）会自动 URL 编码，直接填写原始密码即可。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DORMIOT_MQTT_BROKER_HOST` | localhost | MQTT Broker 地址 |
| `DORMIOT_MQTT_BROKER_PORT` | 1883 | MQTT Broker 端口 |
| `DORMIOT_REDIS_HOST` | localhost | Redis 主机 |
| `DORMIOT_REDIS_PORT` | 6379 | Redis 端口 |
| `DORMIOT_REDIS_DB` | 0 | Redis 数据库编号 |
| `DORMIOT_REDIS_PASSWORD` | | Redis 密码（可选） |
| `DORMIOT_REDIS_USERNAME` | | Redis 用户名（可选） |
| `DORMIOT_MYSQL_HOST` | localhost | MySQL 主机 |
| `DORMIOT_MYSQL_PORT` | 3306 | MySQL 端口 |
| `DORMIOT_MYSQL_USER` | root | MySQL 用户名 |
| `DORMIOT_MYSQL_PASSWORD` | password | MySQL 密码 |
| `DORMIOT_MYSQL_DATABASE` | dormiot | MySQL 数据库名 |
| `DORMIOT_POWER_THRESHOLD_ILLEGAL` | 1500.0 | 违章电器功率阈值 (W) |
| `DORMIOT_POWER_THRESHOLD_OVERLOAD` | 800.0 | 恶性负载功率阈值 (W) |
| `DORMIOT_SMOKE_THRESHOLD_CRITICAL` | 0.40 | 火灾烟雾浓度阈值 (ppm) |

## Systemd 服务配置（生产部署）

创建 `/etc/systemd/system/dormiot.service`：

```ini
[Unit]
Description=DormIoT-Twin Streamlit App
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/DormIoT-Twin
ExecStartPre=/usr/bin/docker compose up -d
ExecStart=/opt/DormIoT-Twin/.venv/bin/streamlit run app.py --server.port 8501 --server.headless true
Restart=always
RestartSec=5
Environment="PATH=/opt/DormIoT-Twin/.venv/bin:/usr/bin"

[Install]
WantedBy=multi-user.target
```

启用并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl enable dormiot
sudo systemctl start dormiot
```

## 告警规则

| 规则 | 条件 | 级别 | 说明 |
|------|------|------|------|
| 违章电器 | 功率 > 1500W | HIGH | 检测大功率违规电器 |
| 恶性负载 | 功率 > 800W | MEDIUM | 负载超过安全阈值 |
| 火灾特级 | 烟雾 > 0.40ppm | CRITICAL | 疑似火灾 |

同设备同类告警有 60 秒冷却时间，避免重复触发。

## License

MIT
