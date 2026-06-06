# OpsAutomationPlateform

面向中小规模 Linux 服务器环境的轻量级自动化运维平台，集成监控展示、告警通知、脚本执行与定时任务。

## 功能特性

- **服务器管理** — 主机台账（IP、SSH 凭据、用途、负责人）、在线检测、Prometheus 采集目标自动同步
- **监控展示** — 基于 node_exporter + Prometheus 的 CPU / 内存 / 磁盘图表
- **告警管理** — 规则配置（CPU、内存、磁盘、TCP 连接、主机存活）、级别、持续时间、屏蔽、邮件通知
- **通知管理** — 通知对象、通知组，支持告警规则与定时任务复用
- **自动化运维** — 脚本管理、手动执行、执行历史导出、Cron 定时任务及失败/成功邮件通知
- **仪表盘** — 告警统计、趋势图、服务器资源 Top 5

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI、SQLAlchemy、PostgreSQL、Redis |
| 前端 | Vue 3、Element Plus、Pinia、ECharts |
| 监控 | Prometheus、node_exporter |
| 部署 | Docker、Docker Compose、Nginx |

## 项目结构

```
ops-automation-plateform/
├── backend/
├── frontend/
├── prometheus/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
└── README.md
```

## 快速开始

### 前置要求

#### 1. 部署 OpsAutomationPlateform 的机器

需要 **Docker Engine 20.10+**，以及 **Docker Compose 1.29+** 或 **Compose V2 插件**。

> 本项目使用 Ubuntu 24.04 作为开发环境

**Ubuntu 24.04（apt 安装）：**

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker

# 当前用户免 sudo 运行 docker（执行后需重新登录 shell）
sudo usermod -aG docker "$USER"
```

验证：

```bash
docker --version
docker-compose --version
# 若已安装 Compose V2 插件，也可执行：docker compose version
```

**可选：安装 Docker 官方 Compose V2 插件**（与上文的 `docker-compose` 二选一即可）：

```bash
sudo apt install -y docker-compose-v2
docker compose version
```

> 下文命令以 `docker compose`（V2）为例。若只有 V1，请将 `docker compose` 替换为 `docker-compose`（例如 `docker-compose up -d --build`）。

#### 2. 被管服务器（监控 / 告警功能需要）

每台需采集指标的主机应安装 [node_exporter](https://github.com/prometheus/node_exporter)，默认监听 **9100** 端口。  
以下示例为 **linux-amd64**；其他架构请到 [Releases](https://github.com/prometheus/node_exporter/releases) 选择对应包。

```bash
wget --no-check-certificate --retry-connrefused --tries=5 \
  https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz

tar xvfz node_exporter-1.6.1.linux-amd64.tar.gz
cd node_exporter-1.6.1.linux-amd64

# 前台启动（测试用）
./node_exporter &
```

验证（在被管服务器上执行）：

```bash
curl -s http://127.0.0.1:9100/metrics | head
```

生产环境建议配置为 systemd 服务，保证重启后自启；仅做功能验证时，上述后台启动即可。

配置 systemd 示例：
```
# 创建服务文件
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/root/node_exporter-1.6.1.linux-amd64/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动并设置开机自启
systemctl daemon-reload
systemctl start node_exporter
systemctl enable node_exporter
```

平台侧还需能访问被管机的 **9100**（Prometheus 拉取指标）和 **22**（脚本执行、在线检测，端口可在主机台账中修改）。

#### 3. SSH 要求（脚本执行 / 自动化运维）

若需使用 **脚本执行**、**定时任务** 等自动化功能，被管服务器须满足：

- **sshd 已启动**，且平台能访问 SSH 端口（默认 22，可在台账中修改）
- **允许密码登录**：平台通过 SSH 用户名 + 密码连接，不使用密钥。被管机 `sshd` 需开启密码认证，例如：

```bash
# 检查 sshd 配置（不同发行版路径可能为 /etc/ssh/sshd_config.d/*.conf）
grep -E '^PasswordAuthentication' /etc/ssh/sshd_config

# 若 PasswordAuthentication 为 no，需改为 yes 后重载 sshd
# PasswordAuthentication yes
sudo systemctl reload sshd   # 或 sshd / ssh
```

- 台账中填写的 **SSH 用户名、密码正确**；添加或编辑主机时可点击 **「测试连接」** 验证，避免保存错误凭据后执行脚本才失败

> **说明：** 仅使用监控 / 告警（node_exporter）时，不要求 SSH 密码认证可用；但主机存活检测、脚本与定时任务均依赖 SSH。

### 1. 克隆并配置

```bash
git clone https://github.com/chainless015/ops-automation-plateform
cd ops-automation-plateform

cp .env.example .env
# 编辑 .env：至少修改 SECRET_KEY；需要邮件通知时配置 SMTP
```

### 2. 启动

```bash
docker compose up -d --build
```

### 3. 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost |
| API 文档 | http://localhost:8000/api/docs |
| Prometheus | http://localhost:9090 |

**默认账号：** `admin` / `admin123`（**仅首次初始化时生效**，登录后请尽快修改密码）

### 4. 验证

```bash
docker compose ps
curl http://localhost:8000/health
# {"status":"healthy"}
```

## 环境变量

见 [.env.example](.env.example)。主要项：

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | JWT 签名密钥（至少 32 字符） |
| `ENCRYPTION_KEY` | SSH 密码 Fernet 密钥（44 位 url-safe Base64） |
| `SMTP_*` | 邮件通知（可选） |
| `TZ` / `PGTZ` | 时区，默认 `Asia/Shanghai` |

## 服务说明

| 容器 | 端口 | 说明 |
|------|------|------|
| frontend | 80 | Nginx 静态资源 + `/api` 反向代理 |
| backend | 8000 | FastAPI 应用 |
| postgres | 5432 | 数据库 |
| redis | 6379 | 验证码缓存 |
| prometheus | 9090 | 指标采集 |

## 被管服务器接入

1. 按上文 **前置要求 → 被管服务器** 安装 node_exporter
2. 若使用脚本或定时任务，确认被管机 **SSH 已开启密码认证**（见上文 **SSH 要求**）
3. 在平台「服务器管理」中添加主机（IP、SSH 账号、用途等），建议先 **测试连接** 再保存
4. 添加后平台会自动将目标写入 Prometheus；在 Prometheus UI 或「主机存活」告警中确认 `up` 为 1

## 开发说明

### 生产模式

```bash
docker compose up -d
# 浏览器访问 http://localhost
# 前端 /api → Nginx → backend
```

修改代码后重新构建：

```bash
docker compose up -d --build frontend   # 仅前端
docker compose up -d --build backend    # 仅后端
```

### 前端热更新

```bash
docker compose up -d   # 先启动后端等依赖

cd frontend
npm install
npm run dev
# 浏览器访问 http://localhost:5173
# Vite 将 /api 代理到 localhost:8000，无需修改 vite.config.js
```

环境变量见 `frontend/.env.development`（`VITE_API_BASE_URL` 留空即可）。

### 本地跑后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 常见问题

### 端口被占用

修改 `docker-compose.yml` 中对应 `ports` 映射，例如 `"8080:80"`。

### 数据库重新初始化

```bash
docker compose down -v
docker compose up -d
```

### 告警邮件发不出

检查 `.env` 中 SMTP 配置，修改后需重建 backend：

```bash
docker compose up -d --force-recreate backend
```

## 停止服务

```bash
docker compose down        # 保留数据卷
docker compose down -v     # 清空数据库等持久化数据
```

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 与 Pull Request。
