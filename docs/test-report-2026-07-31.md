# 测试报告 2026-07-31

> 回归测试：注册 → 登录 → 浏览 → 发书评 → 点赞 完整链路
> 环境：前端 `localhost:5173` / 后端 `localhost:5000` / 数据库 MySQL `mbookti`

## 测试结果总览

| # | 测试项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 注册新账号 | ✅ 通过 | user_id=2，token 正常返回 |
| 2 | 登录 | ✅ 通过 | 账号密码校验成功 |
| 3 | UI 回归（类型页→详情页） | ✅ 通过 | 卡片/AI按钮/推荐类型聚合/书评区渲染正常 |
| 4 | 发表书评 | ✅ 通过（修复后） | 初测 500 → 修复 recommendation_id 约束 |
| 5 | 点赞 | ✅ 通过 | toggle 三次点击，去重正确 |
| 6 | 数据落库验证 | ✅ 通过 | comments/comment_likes 数据正确 |
| 7 | 注册/登录（重启后复测） | ⏳ 待用户重启后端 | bcrypt 修复需重启加载 |

## 发现并修复的问题（2 个）

### 问题 1：发书评 500 —— `recommendation_id` NOT NULL 约束

- **现象**：`POST /api/v1/comments` 返回 500，`{"error":"数据库操作失败"}`
- **根因**：书评重构后 model 中 `recommendation_id` 改为可空（仅兼容旧评论），但 MySQL 表结构仍是 `NOT NULL`。迁移脚本（`migrate_comments_book.py`）只处理了 `book_id`，遗漏该列 → 新评论写入 NULL 触发 `IntegrityError (1048)`
- **修复**：新增 `backend/scripts/fix_comments_recommendation_nullable.py`，执行 `ALTER TABLE comments MODIFY COLUMN recommendation_id INT NULL`（幂等）
- **验证**：`SHOW COLUMNS` 确认可空；真实 5000 实例发评论成功（comment_id=2）

### 问题 2：注册/登录 500 —— bcrypt 包安装残缺

- **现象**：`POST /api/v1/auth/register`、`/login` 返回 500；浏览器报 CORS 错误（次生现象：异常响应缺 CORS 头）
- **根因**：`bcrypt` 包安装被破坏 —— `__init__.py` 丢失（仅剩 `_bcrypt.pyd`），`import bcrypt` 后无 `hashpw/gensalt`。此前 `uv run` 重装 bcrypt 时 `_bcrypt.pyd` 被运行中的后端进程占用，删除中断留下残缺安装
- **修复**：
  1. `uv pip install --force-reinstall bcrypt==4.1.3`（恢复 `__init__.py` 等完整包文件）
  2. `backend/app/auth/password.py` 由 passlib 改为直接使用 bcrypt 原生 API（passlib 1.7.4 与 bcrypt≥4.1 不兼容，避免复发）；旧 `$2b$` hash 完全兼容
- **验证**（新进程）：hash 生成/校验 ✅、旧 passlib hash 校验 ✅（`OLD_VERIFY: True`）、ASGI 全链路 注册 200 / 登录 200 / 评论 200

## 测试数据（已落库）

- 测试账号：`mbti_test_0731154311`（user_id=2）/ `asgi_reg`（user_id=3）/ `fix_verify` / `httpx_*`
- 书评：comment 1（旧，user=1）· 2（user=2，API 回归）· 3（user=3，ASGI 验证）
- 点赞：comment_likes 2 条（user1→comment1、user2→comment2），toggle 去重正确

## 遗留事项

1. **用户重启 5000 后端**（加载修复后 bcrypt 模块 + password.py），重启后复测注册/登录
2. 浏览器 UI 注册复测（Playwright 环境因 web-security 特性无法真实模拟 preflight，建议真实浏览器验证）

---

## 追加：用户个人中心功能验证（同日）

> 环境：后端 ASGI（真实 MySQL）+ 前端 dev server + Playwright 浏览器

### 后端全链路（ASGITransport 真实 MySQL，verify_profile.py）

| # | 测试项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 注册新账号 | ✅ 通过 | profile_test 注册 200 |
| 2 | GET /users/me | ✅ 通过 | 初始 stats 全 0 |
| 3 | PUT /users/me 设置 MBTI | ✅ 通过 | mbti_type_id=1 → INTJ/建筑师 回显 |
| 4 | PUT /users/me 同名 username | ✅ 通过 | 同名不冲突（200） |
| 5 | PUT /users/me/password 错误旧密 | ✅ 通过 | 400 |
| 6 | PUT /users/me/password 正确 | ✅ 通过 | 200 |
| 7 | 旧密码登录 | ✅ 通过 | 401 |
| 8 | 新密码登录 | ✅ 通过 | 200 |
| 9 | 发表书评 | ✅ 通过 | comment id=4 |
| 10 | GET /users/me/comments | ✅ 通过 | total=1，book_title 正确 |
| 11 | POST /users/me/favorites/{id} toggle on | ✅ 通过 | is_favorited=true |
| 12 | GET /users/me/favorites | ✅ 通过 | 列表 1 条 |
| 13 | GET /users/me stats.favorite_count | ✅ 通过 | 1 |
| 14 | GET /books/{id} is_favorited | ✅ 通过 | 登录 true / 无 token false |
| 15 | toggle off | ✅ 通过 | 列表清空 |
| 16 | DELETE /comments/{id} 自己的 | ✅ 通过 | 200 + 点赞记录清理 |
| 17 | DELETE /comments/{id} 他人的 | ✅ 通过 | 403 |
| 18 | GET /users/me 未登录 | ✅ 通过 | 401 |

### 前端 UI 冒烟（Playwright，真实浏览器）

| # | 测试项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 登录 → 首页 MBTI 高亮 | ✅ 通过 | INTJ 卡片带"我的"徽章 + ring |
| 2 | 导航栏头像入口 | ✅ 通过 | 首字母头像 + 用户名 → /profile |
| 3 | /profile 渲染 | ✅ 通过 | 头像/用户名/INTJ 徽章/email/注册日期/统计 0-0-0 |
| 4 | Tabs + 空态 | ✅ 通过 | 我的书评(0) / 我的收藏(0) 空态文案正确 |
| 5 | 详情页收藏 toggle | ✅ 通过 | 收藏 → 已收藏（本地即时翻转） |
| 6 | 收藏统计联动 | ✅ 通过 | profile 收藏计数 0→1，收藏 Tab 列表渲染书籍卡片 |
| 7 | 编辑资料弹窗 | ✅ 通过 | MBTI 下拉 16 项 + 未设置 |
| 8 | MBTI 保存 → 首页高亮联动 | ✅ 通过 | INTP 保存后首页高亮从 INTJ 切至 INTP |
| 9 | 取消收藏 | ✅ 通过 | 已收藏 → 收藏，计数回 0 |

### 测试数据清理

- profile_test MBTI 已还原为 INTJ，收藏已取消（收藏 0）
- 测试书评（comment id=4）已删除，profile_test2 保留为后续手工验证账号

### 验证结论

个人中心后端 18 项 API 验证 + 前端 9 项 UI 冒烟全部通过，无遗留阻塞问题。改动未提交，待分域 commit。

---

## 追加：安全加固验证（同日）

> 加固范围：改密后旧 token 失效 / 登录限流 / admin 角色启用

### 加固内容

| # | 加固项 | 改动 | 原风险 |
|---|--------|------|--------|
| 1 | 改密后旧 token 立即失效 | `users.password_changed_at` 新列（迁移 `scripts/add_password_changed_at.py`）；`jwt.py` 签发带 `iat`；`deps.py` 校验 `iat >= password_changed_at`；改密端点记录时间 | JWT 自包含，改密后旧 token 7 天内仍有效 |
| 2 | 登录/注册限流 | `app/core/ratelimit.py` 内存滑动窗口：同 IP 20 次失败/5min、同用户名 5 次失败/5min（429）、同 IP 10 次注册/5min；`auth.py` 接入 | 无限流，可暴力破解 / 批量注册 |
| 3 | admin 角色启用 | `deps.py` 新增 `get_current_admin`（非管理员 403）；`users.py` 新增 `GET /users`（admin 分页列表） | `is_admin` 字段存在但零使用 |

### 验证结果（ASGI 全链路，13/13 PASS）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | 新 token 访问 /me | ✅ 200 |
| 2 | 改密码 | ✅ 200 |
| 3 | **改密后旧 token 立即失效** | ✅ 401 |
| 4 | 新密码登录后新 token 正常 | ✅ 200 |
| 5 | 普通用户 GET /users | ✅ 403 |
| 6 | 提升 admin 后 GET /users | ✅ 200，total=12 |
| 7 | 同用户名连续 5 次错误登录 | ✅ 前 5 次 401 |
| 8 | **第 6 次触发限流** | ✅ 429 |
| 9 | 限流窗口内正确密码也被拒 | ✅ 429 |
| 10-13 | 回归：发评论/收藏/统计/detail is_favorited | ✅ 全部通过 |

### 遗留事项（本次加固新增）

1. **重启 5000 后端进程**（pid 27960 仍运行加固前代码），重启后限流与旧 token 失效策略生效
2. 限流为**单进程内存实现**：多 worker / 多实例部署需换 Redis 共享存储（ratelimit.py 顶部已注释说明）
3. admin 已用起来（GET /users），但尚无前端管理页面；如需内容审核（删任意评论/下架书籍）可基于 `get_current_admin` 扩展
4. 兼容性说明：存量用户 `password_changed_at=NULL` 不触发失效检查，首次改密后启用；老 token（无 iat）对未改密用户不受影响

---

## 追加：第二轮安全加固（同日，17/17 验证通过）

### 加固项与验证结果

| # | 等级 | 加固项 | 实现 | 验证 |
|---|------|--------|------|------|
| 1 | 🔴 严重 | **JWT 密钥** | `.env` 写入 64 字符随机 `JWT_SECRET_KEY`；`config.py` 拒绝空/默认密钥（启动 fail-fast） | 非默认密钥 len=64 ✅ |
| 2 | 🟠 高 | **代理 SSRF 精确白名单** | `proxy.py` 用 `urlparse` 校验：仅 https + `img[N].doubanio.com` 域名（拒绝 IP/端口/userinfo/子串绕过） | 7 个绕过向量全拦截 ✅，合法 URL 放行 ✅ |
| 3 | 🟠 高 | **输入校验** | username 3-50 + 字符集、password ≥6、email 格式（EmailStr）、评论 ≤2000、URL ≤2048 | 弱注册/空评论/超长评论 → 422 ✅，合法注册/评论正常 ✅ |
| 4 | 🟡 中 | **安全响应头** | 中间件：`X-Content-Type-Options: nosniff`、`X-Frame-Options: SAMEORIGIN`、`Referrer-Policy: strict-origin-when-cross-origin` | 三头全部生效 ✅ |
| 5 | 🟡 中 | **docs 生产关闭** | `debug` 配置（默认 False）：非调试时 `docs_url/redoc_url/openapi_url=None`；本地 `.env` 设 `DEBUG=true` | DEBUG=true 时 /docs 可用 ✅ |
| 6 | 🟢 低 | **前端 401 全局拦截** | axios 响应拦截器：非登录/注册端点的 401 → 清 token/user → 跳 /login | vue-tsc + build 通过 ✅ |
| 7 | 🟢 低 | **DB_URL 打码** | `print_config()` 隐藏数据库密码 | 代码审查 ✅ |

### 回归验证（新密钥下全链路）

GET /me · 发评论 · 收藏 toggle · 改密码 · 改密后旧 token 失效 401 · 新 token detail is_favorited —— 全部通过 ✅

### 注意事项

1. **JWT 密钥变更 → 所有已签发的旧 token 失效**，已登录用户需重新登录（预期行为，本地开发无影响）
2. `.env` 为 gitignored，密钥不会入库；部署新环境需重新生成
3. 弱注册 422 后前端注册表单会收到 FastAPI 校验错误（detail 为数组），如前端要更友好的提示可后续同步

---

## 追加：通知系统（同日，后端 20/20 验证通过）

> 双通道方案：公告走主页弹窗+确认按钮（未登录用 sessionStorage 兜底），个人通知走铃铛+收件箱页

### 实现内容

| # | 模块 | 改动 |
|---|------|------|
| 1 | 数据表 | `announcements` / `announcement_acks`（UNIQUE(announcement_id, user_id)）/ `notifications`（user_id FK CASCADE + index）三表；迁移 `scripts/create_notification_tables.py`（幂等）已执行 |
| 2 | 公告路由 | `GET /announcements/unacked`（可选登录，未登录返回 active 前 3 条）；`POST /{id}/ack` 确认；admin `POST ""` 发布 / `GET` 列表 / `DELETE {id}` 下线 |
| 3 | 通知路由 | `GET /notifications` / `GET /unread-count` / `POST /{id}/read` / `POST /read-all` / admin `POST /to/{user_id}` 定向消息；type: 1=评论获赞 2=管理员消息 3=回复（预留） |
| 4 | 获赞触发 | `comments.py` toggle_like：非自赞且该用户对同评论无既有通知时插入"你的书评被 X 赞了"（取消再赞不重复）；携带 related_book_id/related_comment_id 供跳转 |
| 5 | 权限 | 通知仅本人可见（越权 404）；公告发布/下线仅 admin（普通用户 403） |
| 6 | 前端 | `App.vue` 铃铛+未读红点（30s 轻量轮询，未登录隐藏）；`NotificationsPage.vue`（/notifications，requiresAuth，单条已读/全部已读/点击跳书）；`HomePage.vue` 公告弹窗+我知道了按钮 |

### 验证结果（ASGI 全链路 + 真实 MySQL，20/20 PASS）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | A 赞 B 评论 → B 未读 +1 | ✅ |
| 2 | 通知内容含赞者昵称 + 评论/书籍跳转 id | ✅ |
| 3 | **取消赞再赞不重复通知** | ✅（修复后） |
| 4 | 自己赞自己不通知 | ✅ |
| 5 | 单条标记已读 → 未读回落 | ✅ |
| 6 | 读他人通知 → 404（越权拦截） | ✅ |
| 7 | admin 发布公告 | ✅ |
| 8 | 普通用户发布公告 → 403 | ✅ |
| 9 | 未登录用户可见公告 | ✅ |
| 10 | 未确认用户可见公告 | ✅ |
| 11 | 确认后不再推送 | ✅ |
| 12 | admin 下线公告 → 全端不再推送 | ✅ |
| 13 | 定向消息给不存在用户 → 404 | ✅ |
| 14 | admin 定向消息 → 接收方未读 +1、内容正确 | ✅ |
| 15 | 全部已读 | ✅ |

### 验证中修复的问题

- **取消赞再赞重复通知**：初次实现 toggle_like 每次点赞都插通知；修复为插入前查重（同 user_id + type=1 + related_comment_id 已存在则不重复），20/20 复测通过

### 注意事项

1. 前端 vue-tsc + vite build 通过（HomePage/App/NotificationsPage 改动后）
2. 通知轮询为前端 30s 间隔 + 路由切换刷新，实时性要求高可后续升级 WebSocket/SSE
3. 后端 5000 进程仍未重启（旧代码旧密钥）；验证基于 ASGI 直连新代码，真实浏览器联调需重启后端
4. `notifications` 表类型 3（评论被回复）预留未触发，待评论回复功能落地时接入

---

## 追加：管理后台（同日，后端 13/13 验证通过）

> 隐藏管理界面：仅管理员可见可访问（普通用户无入口、访问 /admin 重定向首页、接口 403），支持发布/下线系统公告 + 对特定用户发送管理员消息

### 实现内容

| # | 模块 | 改动 |
|---|------|------|
| 1 | 后端 schema | `UserResponse` / `UserProfileResponse` 增加 `is_admin` 字段 → 登录/注册/`/me`/用户列表均返回管理员标识 |
| 2 | 前端路由 | `/admin`（meta: requiresAuth + requiresAdmin）；守卫：非管理员访问重定向首页，界面不可见 |
| 3 | AdminPage.vue | 双 Tab：**公告管理**（发布表单 1-100/1-5000 字校验 + 已发布列表 + 下线按钮）、**用户消息**（用户列表 50 人/页 + 按用户名/ID 过滤 + 选中高亮 + 发送消息）；组件内二次校验非管理员即跳转 |
| 4 | 导航入口 | App.vue 管理图标（齿轮），仅 `user?.is_admin` 时渲染，普通用户导航中完全不可见 |
| 5 | 前端 api | `publishAnnouncement` / `getAnnouncementList` / `deactivateAnnouncement` / `getUsers` / `sendAdminMessage` |

### 验证结果（ASGI 全链路，13/13 PASS）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | 注册返回 user.is_admin=False | ✅ |
| 2 | 普通用户发布公告 → 403 | ✅ |
| 3 | 普通用户看用户列表 → 403 | ✅ |
| 4 | 普通用户看公告列表 → 403 | ✅ |
| 5 | 普通用户发定向消息 → 403 | ✅ |
| 6 | 提权后登录返回 is_admin=True | ✅ |
| 7 | /me 返回 is_admin=True | ✅ |
| 8 | admin 发布公告 | ✅ |
| 9 | admin 公告列表可见 | ✅ |
| 10 | admin 用户列表（分页） | ✅ |
| 11 | 用户列表含 is_admin 字段 | ✅ |
| 12 | admin 定向消息 | ✅ |
| 13 | admin 下线公告 | ✅ |

### 注意事项

1. **is_admin 存在用户登录态快照里**：测试中临时提权后需**重新登录**才能看到管理入口（localStorage 的 user 是登录时写入的）
2. 后端所有管理接口由 `get_current_admin` 保护（403），前端隐藏只是体验层，安全以接口为准
3. 验证脚本向 user_id=1 发了一条"管理后台验证消息"测试数据，无实际影响

---

## 追加：路由切换数据丢失 Bug（同日，已修复并验证）

> 现象（用户报告）：从主页点铃铛进通知页 → 页面数据丢失（main 空白）；再点其他页面也空白；**刷新后恢复**

### 根因（Playwright 复现铁证）

- **现象还原**：点击铃铛后 main 区域完全空白（连标题都没有），`GET /notifications` 请求**从未发出**；console 刷屏警告 `Component inside <Transition> renders non-element root node that cannot be animated`
- **根因**：`App.vue` 用 `<Transition mode="out-in">` 包裹路由组件（要求**单根节点**）。通知功能给 `HomePage.vue` 加公告弹窗时，弹窗 div 被放在模板**根级**（与主 div 平级）→ HomePage 变成**双根节点** → Transition 无法完成动画 → **离开动画结束后 enter 不触发 → 新页面组件永远不挂载**（main 空白）
- 这解释了全部现象：`GET /notifications` 没发出（组件没挂载）→ 空白；空白页再切换同样异常（根因仍在）→ 所有页面空白；刷新 → 应用重载 → 首页单根正常渲染 → 恢复

### 修复

- **`HomePage.vue`**：公告弹窗 `<div v-if="currentAnnouncement">` 从模板根级**移入主根 div 内部**，恢复单根节点；加注释防止回归

### 验证（Playwright 全链路）

| # | 场景 | 结果 |
|---|------|------|
| 1 | 修复前复现：点铃铛 → main 空白 + 无 GET /notifications + Transition 警告刷屏 | ✅ 复现（修复前） |
| 2 | 修复后：首页 → 通知页 | ✅ 正常（标题/全部已读/通知项渲染） |
| 3 | 修复后：通知页 → 首页 | ✅ 16 个 MBTI 卡片正常 |
| 4 | 修复后：首页 → 类型页 /types/INTJ | ✅ 推荐书单完整 |
| 5 | 修复后：公告弹窗回归（新公告弹出 + 首页卡片同时正常） | ✅ 单根内弹窗不影响渲染 |
| 6 | vue-tsc + vite build | ✅ 通过 |

### 关联发现（未修，记录备查）

- **潜在坑**：后端 `HTTPBearer` 在**缺少** Authorization header 时返回 **403**（而非 401），而前端 axios 拦截器只处理 401 → 若 token 被清但页面未刷新，后续请求会 403 被各页面 catch 静默吞掉显示空列表（不会跳登录）。当前代码路径（401 拦截器带跳转）不会触发，但建议后续拦截器补 403 处理

---

## 追加：忘记密码功能（方案 C：管理后台重置 + 邮箱重置骨架，已实现并验证）

> 需求：用户忘记密码的处理。选定方案 C —— 管理后台重置（立即可用）+ 邮箱重置接口骨架（dev 模式返回 token，生产接 SMTP 即用）。

### 后端改动

| 文件 | 内容 |
|---|---|
| `app/models/password_reset_token.py` | 新增 `PasswordResetToken` 模型（token_hash CHAR(64) 存 sha256、expires_at、used_at） |
| `scripts/create_password_reset_tokens.py` | 幂等建表迁移（SHOW TABLES 判存在） |
| `app/services/email.py` | 邮件 stub：`send_password_reset_email`（SMTP 未配置打日志返回 False；465 SSL / 587 STARTTLS） |
| `app/config.py` | 新增 SMTP_HOST/PORT/USER/PASSWORD/FROM（默认空 = 未配置） |
| `app/schemas/user.py` | `ForgotPasswordRequest` / `ResetPasswordRequest` / `AdminResetPasswordRequest` |
| `app/routers/auth.py` | `POST /auth/password/forgot`（dev 返回 token / 生产防枚举）+ `POST /auth/password/reset`（校验 token + 更新 password_changed_at） |
| `app/routers/users.py` | `PUT /users/{user_id}/password`（admin 重置，get_current_admin 保护） |
| `scripts/upgrade_password_changed_at_precision.py` | **加固**：`password_changed_at` 列 DATETIME → DATETIME(6)（微秒精度，修复同秒失效边界） |

### 安全设计

- **token 只存 sha256 哈希**，明文仅经邮件/dev 响应一次性交给用户
- **防邮箱枚举**：用户不存在也返回 200 同文案
- **一次性**：used_at 非空即失效；30 分钟过期
- **旧 token 立即失效**：reset/重置更新 `password_changed_at`，复用既有"改密后旧 token 失效"机制
- **限流**：forgot 每 IP 10 分钟最多 5 次（429）
- **admin 保护**：重置他人密码需 `get_current_admin`（403）

### 后端全链路验证（HTTP 真实服务 + 真实 MySQL）

| # | 场景 | 结果 |
|---|------|------|
| 1 | forgot 返回 dev token | ✅ |
| 2 | forgot 防枚举（不存在邮箱 200 无 token） | ✅ |
| 3 | reset 成功 | ✅ |
| 4 | **reset 后旧 token 立即失效（401）** | ✅（DATETIME(6) 修复后） |
| 5 | 旧密码登录 401 | ✅ |
| 6 | 新密码登录 200 | ✅ |
| 7 | reset token 一次性（复用 400） | ✅ |
| 8 | 无效 token 400 | ✅ |
| 9 | admin 重置他人密码 200 | ✅ |
| 10 | 非 admin 重置他人 403 | ✅ |

### 前端浏览器验证（Playwright）

| # | 场景 | 结果 |
|---|------|------|
| 1 | 登录页"忘记密码？"链接 | ✅ |
| 2 | 忘记密码页：输邮箱 → dev token 显示 + 下一步 | ✅ |
| 3 | 重置密码页：token 自动预填 → 新密码 → 成功跳登录 | ✅ |
| 4 | 登录页 success=1 提示"密码重置成功" | ✅ |
| 5 | 新密码登录成功 | ✅ |
| 6 | AdminPage 用户消息 Tab：重置密码卡片（选用户→填密码→重置成功提示） | ✅ |
| 7 | vue-tsc + vite build | ✅ |

### 测试数据清理

- profile_test / profile_test2 密码已还原为 `demo1234`，profile_test is_admin 已还原 false
- password_reset_tokens 表测试 token 已清空

### 备注

- **dev 模式**：未配置 SMTP 时 forgot 响应 `data.reset_token` 携带明文 token（仅开发可见），生产配置 SMTP 后自动走邮件、data 为 null
- **已知边界**：`PUT /users/me/password` 会被更具体的 change_password 路由先匹配（admin 重置端点的 `user_id=="me"` 防御是死代码，无害）
