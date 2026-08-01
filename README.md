# MBookTI

> 根据 MBTI 人格类型推荐书籍的 AI 应用

通过 MBTI 人格测评类型，结合 DeepSeek AI 生成个性化书籍推荐，并支持书评社区、收藏、公告通知等完整功能。

## 功能特性

### 核心功能
- **MBTI 类型展示**：16 种人格类型卡片，含中文/英文名、描述与特质标签
- **AI 智能推荐**：基于 MBTI 类型由 DeepSeek 生成针对性书籍推荐（需登录）
- **书籍详情**：书籍信息、封面（豆瓣抓取）、推荐理由
- **书评社区**：对书籍发表评论、点赞，删除时级联清理

### 用户体系
- 注册 / 登录 / 登出（JWT 认证，Token 有效期 7 天）
- 个人中心：资料编辑（用户名、MBTI 类型）、修改密码、我的评论、我的收藏
- 忘记密码 / 重置密码（邮件发送，支持 SMTP 或开发模式直显）

### 运营管理
- **管理后台**：公告管理、用户管理等（需管理员账号）
- **系统公告**：未读公告弹窗提醒，支持确认/忽略
- **个人通知**：评论获赞通知、管理员消息

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite 8 + Vue Router + Pinia + Tailwind CSS 4 |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| 数据库 | MySQL 8 |
| AI | DeepSeek API（OpenAI 兼容协议） |
| 认证 | JWT (python-jose) + bcrypt 密码哈希 |
| 部署 | Docker Compose（MySQL + FastAPI + Nginx） |

## 目录结构

```
MBookTI/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── auth/            # JWT 认证、依赖注入
│   │   ├── core/            # 异常处理、限流、配置
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── routers/         # API 路由（auth/users/books/comments 等）
│   │   ├── schemas/         # Pydantic 校验模型
│   │   ├── seed/            # 初始数据（MBTI 类型）
│   │   ├── services/        # 业务逻辑（邮件、豆瓣封面、AI）
│   │   ├── config.py        # 环境变量配置
│   │   ├── database.py      # 数据库连接
│   │   └── main.py          # 应用入口
│   ├── scripts/             # 运维脚本（迁移、数据导入等）
│   ├── Dockerfile
│   └── entrypoint.sh
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/             # API 请求封装
│   │   ├── composables/     # 组合式函数（登录态、i18n）
│   │   ├── router/          # 路由配置（含登录守卫）
│   │   ├── views/           # 页面组件
│   │   └── main.ts          # 入口
│   ├── Dockerfile
│   └── nginx.conf           # 生产 Nginx 配置
├── docker-compose.yml       # Docker 编排
└── docs/                    # 开发文档与测试报告
```

## 快速开始

### 方式一：Docker Compose 部署（推荐）

**前置要求**：Docker + Docker Compose

#### 1. 准备环境变量文件 `.env.docker`

```bash
# 在项目根目录创建 .env.docker（已加入 .gitignore，不会误提交）
MYSQL_ROOT_PASSWORD=你的数据库密码
JWT_SECRET_KEY=你的JWT密钥
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

生成强随机 JWT 密钥：
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> 环境变量**必须配置**：后端启动时会拒绝空/默认 JWT_SECRET_KEY（防止伪造 Token）。

#### 2. 构建并启动

```bash
# 构建镜像并启动（注意必须带 --env-file 指定变量文件）
docker compose --env-file .env.docker up -d --build

# 查看日志（同样带 --env-file，否则会误报变量未设置）
docker compose --env-file .env.docker logs -f backend
```

#### 3. 访问

| 服务 | 地址 | 说明 |
|---|---|---|
| 前端 | http://localhost:8080 | Nginx 托管 Vue 静态文件 + API 反向代理 |
| 后端 API | http://localhost:8000 | FastAPI（生产模式关闭 /docs） |
| MySQL | 127.0.0.1:3307 | 容器端口映射（避开本地 3306） |

#### 4. 导入已有数据（可选）

Docker 的 MySQL 是**全新空库**，只自动初始化 16 条 MBTI 类型。若本地已有开发数据，可用导入脚本迁移：

```bash
cd backend
python scripts/import_local_data_to_docker.py \
  --container mbookti-mysql-1 \
  --container-password 你的数据库密码
```

脚本自动从 `backend/.env` 读取本地库连接，以 utf8mb4 二进制流导出导入（避开 Windows GBK 编码坑），跳过已初始化的 `mbti_types`。

#### 5. 停止

```bash
docker compose --env-file .env.docker down      # 停止（保留数据卷）
docker compose --env-file .env.docker down -v   # 停止并删除数据卷（数据将丢失，谨慎！）
```

### 方式二：本地开发

**前置要求**：Python 3.12+、Node.js 22+、本地 MySQL 8

#### 1. 配置后端

```bash
cd backend
# 复制环境变量模板（若不存在 .env 则创建）
# .env 中至少需要：
#   DB_URL=mysql+asyncmy://root:你的密码@localhost:3306/mbookti?charset=utf8
#   JWT_SECRET_KEY=你的JWT密钥
#   DEBUG=true
#   DEEPSEEK_API_KEY=你的DeepSeek密钥

# 安装依赖（推荐使用 uv）
uv sync
# 或 pip install -e .

# 启动（默认 0.0.0.0:5000，支持局域网/移动设备访问）
uv run python -m app.main
```

开发模式（`DEBUG=true`）会开放 `/docs`（Swagger UI）便于调试。

#### 2. 配置并启动前端

```bash
cd frontend
npm install
npm run dev        # Vite dev server，端口 3000
```

开发模式下前端 API 地址自动跟随当前页面 hostname 拼 `:5000`，桌面访问 `http://localhost:3000`，移动设备经局域网 IP 访问同一端口即可联调。

#### 3. 构建前端（生产预览）

```bash
npm run build      # vue-tsc 类型检查 + vite 构建
npm run preview
```

## 环境变量说明

### 后端（backend/.env）

| 变量 | 必填 | 说明 |
|---|---|---|
| `DB_URL` | ✅ | 数据库连接串，如 `mysql+asyncmy://root:pass@localhost:3306/mbookti?charset=utf8` |
| `JWT_SECRET_KEY` | ✅ | JWT 签名密钥（空/默认值会拒绝启动） |
| `DEBUG` | 开发必填 | `true` 开启 /docs 与调试；生产必须 `false` |
| `DEEPSEEK_API_KEY` | 条件 | 未配置则 AI 推荐功能不可用 |
| `SMTP_HOST` | 条件 | 配置后忘记密码走真实邮件；留空则开发模式回传明文 Token |
| `SMTP_PORT` | | 465 走 SSL / 587 走 STARTTLS |
| `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | | 邮件账号与发件人 |

### 前端（frontend/.env）

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE_URL` | 生产构建时注入的 API 地址（Docker 中默认 `/api/v1` 同源代理） |

## 常见问题

### 1. `docker compose` 提示变量未设置
`docker compose logs` / `config` 等命令若不带 `--env-file`，会因找不到默认 `.env` 而报变量警告。**所有 docker compose 命令都需带 `--env-file .env.docker`**。

### 2. 3306 / 80 端口被占用
本地已有 MySQL（3306）或其他服务（80）时，Docker 映射会冲突。本项目已改为 **3307→3306**、**8080→80**。若仍冲突，可自行修改 `docker-compose.yml` 的 `ports`。

### 3. Docker 库中登录 401
Docker MySQL 是空库，无用户数据。用导入脚本迁移本地数据，或先在前端注册新账号。

### 4. 忘记密码收不到邮件
未配置 SMTP 时：开发模式（`DEBUG=true`）接口直接返回重置 Token；生产模式返回统一文案（不泄露邮箱是否注册），需配置 SMTP 才能发信。

### 5. 密码字段是 bcrypt 哈希，不能直接写明文
修改 `users.password_hash` 时必须写入 bcrypt 哈希（`$2b$12$...`），否则登录永远失败。

## 文档

- [用户个人中心指南](docs/user-profile-guide.md)
- [书详情功能指南](docs/book-detail-feature-guide.md)
- [测试报告 2026-07-31](docs/test-report-2026-07-31.md)

## 开发注意事项

- **生产模式**：`DEBUG=false` 时关闭 `/docs`、`/redoc`、`/openapi.json`，CORS 仅放行白名单
- **安全**：JWT 密钥必须强随机；密码使用 bcrypt（cost=12）；登录/注册/忘记密码均有速率限制
- **代码规范**：后端通过 `py_compile` + LSP 校验，前端通过 `vue-tsc` 类型检查后方可构建
- **提交规范**：`type(scope): 中文描述`，如 `fix(backend): 修复xxx`、`feat(frontend): 新增xxx`

## License

MIT © Max3753
