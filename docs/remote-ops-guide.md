# MBookTI 远程运维指南

> 本文档说明：如何在本地电脑上，对运行在阿里云 ECS 服务器上的 MBookTI 项目进行连接、部署、数据管理和日常运维操作。

## 环境总览

```
┌─────────────────────────┐         ┌──────────────────────────────────┐
│  你的本地电脑 (Windows)   │  SSH   │  阿里云 ECS 服务器 (Ubuntu 22.04)  │
│                         │ ─────► │                                  │
│  - Xshell 终端           │        │  Docker 容器:                    │
│  - rz/sz 文件传输        │        │  ├─ mbookti-frontend-1 (8080)   │
│  - MySQL 客户端(可选)     │        │  ├─ mbookti-backend-1  (8000)   │
└─────────────────────────┘        │  └─ mbookti-mysql-1    (3307)    │
                                   └──────────────────────────────────┘
```

### 关键信息速查

| 项目 | 值 |
|---|---|
| 服务器公网 IP | `8.130.175.251` |
| SSH 端口 | 22（root 用户） |
| 项目路径 | `/root/MBookTI` |
| 环境变量文件 | `/root/MBookTI/.env.docker` |
| 前端地址 | `http://8.130.175.251:8080` |
| 后端地址 | `http://8.130.175.251:8000` |
| MySQL 容器端口映射 | 3307（宿主机）→ 3306（容器） |
| MySQL root 密码 | 在 `.env.docker` 中配置（当前为 `142857`） |
| 数据库名 | `mbookti` |

---

## 一、连接服务器

### 1.1 通过 Xshell 连接（推荐，日常使用）

1. 打开 Xshell → 「新建」
2. 填主机 `8.130.175.251`，端口 `22`，协议 SSH
3. 连接后输入用户名 `root`、密码（阿里云控制台设置的实例密码）
4. 登录成功出现 `root@iZb1dt3kae5m8vZ:~#` 提示符

> **原理**：SSH（Secure Shell）通过 22 端口建立加密通道。阿里云安全组必须放行入方向 `TCP 22/0.0.0.0/0` 才能连上。

### 1.2 通过 Workbench 网页终端连接（备用）

当本地 SSH 连不上（网络故障、安全组误改）时：

1. 登录阿里云控制台 → 云服务器 ECS → 实例列表
2. 点实例 ID → 「远程连接」→「通过 Workbench 远程连接」
3. 输入 root 密码即可进入终端

> **原理**：Workbench 走阿里云**内部管理通道**（VPC 内网），不经过公网 22 端口，因此即使公网 SSH 被防火墙挡住也能连。它和 Xshell 看到的是同一个系统，命令完全通用。

---

## 二、查看项目状态

### 2.1 查看三个容器运行状态

```bash
cd /root/MBookTI
docker compose --env-file .env.docker ps
```

正常输出示例：

```
NAME                 IMAGE              STATUS                   PORTS
mbookti-backend-1    mbookti-backend    Up                       0.0.0.0:8000->8000/tcp
mbookti-frontend-1   mbookti-frontend   Up                       0.0.0.0:8080->80/tcp
mbookti-mysql-1      mysql:8            Up (healthy)             0.0.0.0:3307->3306/tcp
```

> **原理**：`docker compose` 通过根目录 `docker-compose.yml` 编排三个容器。`--env-file .env.docker` 提供 MySQL 密码、JWT 密钥等敏感变量。**必须带上这个参数**，否则 compose 找不到变量会误报警告。
>
> `Up (healthy)` 表示容器通过健康检查（MySQL 用 `mysqladmin ping` 每 5 秒探测一次）。

### 2.2 查看后端日志（排查错误首选）

```bash
docker compose --env-file .env.docker logs --tail 100 backend
```

- `--tail 100`：只看最近 100 行
- `-f` 可实时跟随日志：`docker compose --env-file .env.docker logs -f backend`（Ctrl+C 退出）

> **原理**：`docker compose logs` 读取容器标准输出（STDOUT/STDERR）。后端 Uvicorn 把访问日志和错误都打到标准输出，所以这里能看到全部运行信息。

### 2.3 查看 MySQL 日志

```bash
docker compose --env-file .env.docker logs --tail 50 mysql
```

---

## 三、重启与重新部署

### 3.1 重启单个服务

```bash
docker compose --env-file .env.docker restart backend
```

### 3.2 停止全部（保留数据）

```bash
docker compose --env-file .env.docker down
```

### 3.3 停止并删除数据卷（⚠️ 数据会丢失，慎用）

```bash
docker compose --env-file .env.docker down -v
```

> **原理**：`down` 停止并删除容器，但数据卷（`mysql_data`）保留在宿主机 `/var/lib/docker/volumes/` 下；加 `-v` 会连数据卷一起删除，相当于「格式化数据库」。日常不要加 `-v`。

### 3.4 更新代码并重建

当 GitHub 上有新代码时：

```bash
cd /root/MBookTI
git pull
docker compose --env-file .env.docker up -d --build
```

> **原理**：`git pull` 拉取最新代码；`--build` 重新构建镜像。Docker 有**层缓存**，只重建变更的部分，通常几十秒到几分钟。构建后容器自动重启为新镜像。

---

## 四、进入容器内部操作

### 4.1 进入后端容器（看代码、跑脚本）

```bash
docker exec -it mbookti-backend-1 bash
```

进入后可以直接查看 `/app` 下的代码、执行 Python 命令。退出输入 `exit`。

### 4.2 进入 MySQL 容器并执行 SQL

```bash
# 直接执行单条 SQL
docker exec mbookti-mysql-1 mysql -uroot -p142857 -e "SHOW DATABASES;"

# 进入交互式 MySQL 命令行
docker exec -it mbookti-mysql-1 mysql -uroot -p142857 mbookti
```

> **原理**：`docker exec` 在运行中的容器里执行命令。MySQL 容器内已装 mysql 客户端，`-uroot -p142857` 用 root 身份登录。`-D mbookti` 或末尾跟库名直接进入指定数据库。

---

## 五、数据库数据管理

### 5.1 查看数据量

```bash
docker exec mbookti-mysql-1 mysql -uroot -p142857 -D mbookti -N -e "SELECT 'users',COUNT(*) FROM users UNION ALL SELECT 'books',COUNT(*) FROM books UNION ALL SELECT 'comments',COUNT(*) FROM comments"
```

### 5.2 导出数据库到服务器文件（备份）

```bash
# 在容器内导出到 /tmp，再拷贝到服务器 /root
docker exec mbookti-mysql-1 sh -c "mysqldump -uroot -p142857 --default-character-set=utf8mb4 --single-transaction mbookti > /tmp/backup.sql"
docker cp mbookti-mysql-1:/tmp/backup.sql /root/mbookti_backup.sql
```

### 5.3 从服务器文件导入数据库（恢复）

```bash
docker cp /root/mbookti_dump.sql mbookti-mysql-1:/tmp/dump.sql
docker exec mbookti-mysql-1 sh -c "mysql -uroot -p142857 --default-character-set=utf8mb4 mbookti < /tmp/dump.sql"
```

> **原理**：
> - `mysqldump` 生成完整 SQL 脚本（含 `DROP TABLE IF EXISTS` + `CREATE TABLE` + `INSERT`），导入时会**重建表结构再插入数据**，所以重复导入不会主键冲突。
> - `--default-character-set=utf8mb4` 强制 UTF-8 编码，**防止中文乱码**（Windows 本机 MySQL 客户端默认是 GBK，这是最容易踩的坑）。
> - `docker cp` 用于容器 ↔ 宿主机之间复制文件。

---

## 六、本地 ↔ 服务器文件传输

### 6.1 用 rz/sz（最简单，需 Xshell）

首次使用先安装：

```bash
apt install -y lrzsz
```

**上传文件**（本地 → 服务器）：

```bash
cd /root && rz
```

会弹出文件选择窗口，选中本地文件即可。

**下载文件**（服务器 → 本地）：

```bash
cd /root && sz 文件名
```

弹出保存窗口，选择本地保存位置。

> **原理**：rz/sz 是基于 ZMODEM 协议的文件传输工具，复用 SSH 连接通道，无需额外配置端口。Xshell 原生支持弹窗交互。

### 6.2 用 Xftp 图形化传输

Xshell 工具栏点「新建文件传输」（或 Ctrl+Alt+F）直接打开 Xftp，左右拖拽即可。适合批量传输。

### 6.3 传输数据库文件到服务器后导入

```bash
# 假设本地已 mysqldump 出 mbookti_dump.sql 并 rz 上传到 /root
docker cp /root/mbookti_dump.sql mbookti-mysql-1:/tmp/dump.sql
docker exec mbookti-mysql-1 sh -c "mysql -uroot -p142857 --default-character-set=utf8mb4 mbookti < /tmp/dump.sql"
```

---

## 七、使用项目自带脚本

项目 `backend/scripts/` 下提供两个运维脚本，简化以上手动操作：

### 7.1 本地数据 → Docker 容器（首次部署用）

在**本地** `backend/` 目录执行：

```bash
python scripts/import_local_data_to_docker.py \
  --container mbookti-mysql-1 \
  --container-password 142857
```

自动从本地 MySQL 导出（utf8mb4 二进制流），`docker cp` 进容器并导入，自动验证数据量。

### 7.2 服务器间迁移 / 备份导出（换服务器用）

在**服务器** `/root/MBookTI/backend/scripts/` 执行：

```bash
# 导出备份到 /root/mbookti_backup.sql
python migrate_server.py export --container mbookti-mysql-1 --password 142857

# 在新服务器导入
python migrate_server.py import --container mbookti-mysql-1 --password 新密码 --in /root/mbookti_backup.sql
```

支持 `--dry-run` 预览命令、`--out/--in` 自定义路径。

---

## 八、服务器侧常见操作

### 8.1 查看磁盘占用

```bash
df -h
```

### 8.2 查看内存占用

```bash
free -h
```

### 8.3 容器日志占满磁盘时清理

```bash
docker system prune -f
```

---

## 九、安全提醒

1. **MySQL 密码**：当前 `142857` 是弱密码，生产环境建议改为强密码（修改 `.env.docker` → `docker compose up -d` 重建 → 容器内 `ALTER USER` 改库密码）。
2. **8080/8000 端口暴露公网**：8000 后端 API 建议在安全组收紧（仅自己 IP 可访问），或后续加 Nginx 鉴权。
3. **备份习惯**：定期执行 5.2 的导出，把 `/root/mbookti_backup.sql` 下载到本地保存。试用期到期、换服务器时用 `migrate_server.py` 一键迁移。
4. **JWT 密钥**：`.env.docker` 中的 `JWT_SECRET_KEY` 是生产密钥，不要泄露、不要提交到 Git。

---

## 十、故障排查速查

| 现象 | 排查步骤 |
|---|---|
| 网页打不开 | ① 安全组是否放行 8080 ② `docker compose ps` 看 frontend 是否 Up ③ 本机 `curl http://8.130.175.251:8080` |
| 登录报错 | ① 数据库是否为空（`SELECT COUNT(*) FROM users`）② 密码是否 bcrypt 哈希 |
| 后端启动失败 | `docker compose logs backend` 看报错，常见是 `.env.docker` 变量缺失 |
| SSH 连不上 | ① 安全组 22 端口 ② 用 Workbench 备用通道 ③ 阿里云「一键诊断」 |
| MySQL 中文乱码 | dump/导入时是否都带 `--default-character-set=utf8mb4` |
