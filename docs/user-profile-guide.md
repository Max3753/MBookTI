# 用户个人中心 · 手搓实施清单

> 模式：**用户手写代码**，本清单只提供设计、要点与检查方式，不提供完整代码。
> 范围：A+B+C 全量（资料 / 我的书评 / 收藏 / 统计 / MBTI 联动首页）
> 已确认决策：MBTI 联动首页、默认头像（首字母+色板）、评论硬删、改密码后跳登录

## 总体架构

```
后端（FastAPI + MySQL）
  ├─ 新表 user_book_favorites（收藏）
  ├─ 新路由 routers/users.py（/api/v1/users/me 系列）
  ├─ 改 routers/comments.py（DELETE 自己评论）
  └─ 改 routers/books.py（detail 加 is_favorited）
前端（Vue3 + TS）
  ├─ views/ProfilePage.vue（/profile）
  ├─ App.vue（导航栏用户入口）
  ├─ views/BookDetailPage.vue（收藏按钮）
  └─ views/HomePage.vue（MBTI 高亮联动）
```

---

## 第 1 步：后端 · 收藏表 + 资料接口

### 1.1 建表（手写 SQL 执行或迁移脚本）

```sql
CREATE TABLE IF NOT EXISTS user_book_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_book (user_id, book_id),
    CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_fav_book FOREIGN KEY (book_id) REFERENCES books(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 1.2 model 文件（新 `app/models/favorite.py`）

要点：
- 类名 `UserBookFavorite`，表名 `user_book_favorites`
- 参照 `app/models/comment.py` 的写法（Mapped + mapped_column 风格）
- 记得在 `app/models/__init__.py` 导出（对照现有文件加一行）—— 现有导出顺序：`from app.models.comment_like import CommentLike` 之后追加 `from app.models.favorite import UserBookFavorite`
- **不用迁移工具**：直接对 MySQL 执行上面 SQL 即可（项目没接 alembic）

### 1.3 schema 导出

新 schema 写好后在 `app/schemas/__init__.py` 追加导入 + `__all__` 条目（对照现有 UserResponse/CommentResponse 的写法）。

### 1.3 schema 文件（新 `app/schemas/user.py` 扩展或新文件）

- `UserProfileResponse`：id / username / email / avatar_url / mbti_type_id / mbti_type_code / mbti_type_name / created_at / stats
- `stats` 子对象：`comment_count` / `favorite_count` / `like_received`（我的书评获赞总和）
- `UserUpdateRequest`：username / avatar_url / mbti_type_id（均可选，Partial）
- `ChangePasswordRequest`：old_password / new_password

注意：mbti_type_code/name 需要 join mbti_types 表，或复用现有 `MbtiTypeResponse`

**已核对的可直接用参照**：
- `mbti_types` 表字段：`code`（如 "INTJ"）、`name`（如 "建筑师"）、`name_en` —— join 条件 `User.mbti_type_id == MbtiType.id`
- `get_current_user` 依赖：`from app.auth.deps import get_current_user`（返回 User 对象）
- `MbtiTypeResponse`（app/schemas/mbti_type.py）已有 `id/code/name/name_en/description/traits`

### 1.4 路由（新 `app/routers/users.py`，prefix `/api/v1/users`）

| 端点 | 说明 |
|---|---|
| `GET /me` | 需登录；返回资料+统计（书评数、收藏数、获赞和） |
| `PUT /me` | 需登录；更新 username/avatar_url/mbti_type_id；username 唯一性校验（409/400） |
| `PUT /me/password` | 需登录；校验旧密码 → 新密码 hash 入库 |

要点：
- 依赖 `get_current_user`（参照 comments.py 的用法）
- 统计用聚合查询：`COUNT(comments)`、`COUNT(favorites)`、`SUM(likes_count)`（SQLAlchemy `func.count`/`func.coalesce`）
- `get_current_user` 查出的 user 需 refresh 才能拿到更新后的 mbti 关联信息

### 1.5 main.py 挂载新路由

```python
from app.routers import users
app.include_router(users.router)
```

### 检查方式（写完自测）

```powershell
# 注册/登录拿 token → 带 token 请求
curl.exe -s http://localhost:5000/api/v1/users/me -H "Authorization: Bearer <token>"
curl.exe -s -X PUT http://localhost:5000/api/v1/users/me -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"mbti_type_id\":1}"
```

**验收标准**：
- [ ] GET /me 返回资料 + stats 三个统计字段
- [ ] PUT /me 改 mbti_type_id 后 GET 反映变更
- [ ] PUT /me/password 旧密码错 → 400；对 → 旧密码失效
- [ ] 未登录访问 /me → 401

---

## 第 2 步：后端 · 我的书评 + 删除

### 2.1 `GET /api/v1/users/me/comments`

- 需登录；按 `created_at DESC`；join books 拿 `book_title` + `book_cover_url`
- 返回：id / content / book_id / book_title / book_cover_url / likes_count / created_at / parent_id
- 建议分页参数：`page` / `page_size`（默认 1-20）

**已核对的参照**：Book model 字段 `title` / `cover_url`（`from app.models import Book`）；join 写法参考 books.py 里 detail 接口的 `select(Book, ...)` 模式。

### 2.2 `DELETE /api/v1/comments/{comment_id}`

- 需登录；仅本人可删（`current_user.id != comment.user_id` → 403）
- 硬删：`session.delete(comment)`；同时删该评论的点赞记录（comment_likes 表 `DELETE WHERE comment_id=...`）

### 检查方式

```powershell
curl.exe -s http://localhost:5000/api/v1/users/me/comments -H "Authorization: Bearer <token>"
curl.exe -s -X DELETE http://localhost:5000/api/v1/comments/3 -H "Authorization: Bearer <token>"
```

**验收标准**：
- [ ] 列表含 book_title / book_cover_url
- [ ] 删别人的评论 → 403；删自己的 → 成功且列表消失
- [ ] 删除后该评论点赞记录也被清（查 comment_likes 表）

---

## 第 3 步：后端 · 收藏接口

### 3.1 `POST /api/v1/users/me/favorites/{book_id}`

- 需登录；toggle 语义：已收藏 → 取消（删记录）；未收藏 → 插入
- 返回：`{ is_favorited: bool }`

### 3.2 `GET /api/v1/users/me/favorites`

- 需登录；join books；返回书列表（BookResponse 结构 + favorited_at）
- 按收藏时间倒序

**已核对的参照**：`BookResponse`（app/schemas/book.py）字段齐备，可直接复用；列表外层包 `ApiListResponse`（参照 comments 列表接口）。

### 3.3 `GET /api/v1/books/{book_id}` 响应加 `is_favorited`

- 需**可选登录**：有 token 时查当前用户是否收藏；无 token 返回 false
- 实现：`get_current_user_optional` 依赖（查 header Authorization，无效/缺失 → None，不抛 401）

**提示**：`BookDetailResponse` 加 `is_favorited: bool = False`；可选登录依赖参考 `deps.py` 的 `get_current_user` 改造（去掉 `HTTPBearer(auto_error=False)` 即可），或单独写个轻量依赖。

### 检查方式

```powershell
curl.exe -s -X POST http://localhost:5000/api/v1/users/me/favorites/1 -H "Authorization: Bearer <token>"   # 收藏
curl.exe -s -X POST http://localhost:5000/api/v1/users/me/favorites/1 -H "Authorization: Bearer <token>"   # 再调 → 取消
curl.exe -s http://localhost:5000/api/v1/books/1 -H "Authorization: Bearer <token>"   # is_favorited: true/false
```

**验收标准**：
- [ ] toggle 两次回到原状态，表里无重复记录（UNIQUE 约束兜底）
- [ ] 列表接口按时间倒序
- [ ] 未登录访问 books detail：is_favorited=false 且不报错

---

## 第 4 步：前端 · 资料页

### 4.1 新页面 `ProfilePage.vue`（路由 `/profile`，需登录守卫）

结构：
```
┌ 头部卡 ──────────────────────────┐
│ [默认头像] 用户名 · 邮箱 · 注册时间 │
│ [统计徽章] 书评 N · 收藏 N · 获赞 N │
│ [编辑] 用户名 / MBTI 选择器(16选1)  │
│ [改密码] 弹窗（旧密码+新密码+确认）  │
└──────────────────────────────────┘
┌ Tab ① 我的书评 ──────────────────┐
│ 封面 书名 · 内容 · 时间 · [删除]    │
└──────────────────────────────────┘
┌ Tab ② 我的收藏 ──────────────────┐
│ 书卡网格（复用类型页卡片样式）       │
└──────────────────────────────────┘
```

要点：
- **默认头像**：`username` 首字符 + 色板取色（`username.charCodeAt(0) % 色板长度`），圆形，无图片资源
- 进入页面调 `GET /users/me`，加载态骨架屏（参照 BookDetailPage）
- 未登录访问 → 路由守卫跳 `/login`
- 保存资料后更新 `useAuth` 里 localStorage 的 user 对象
- 改密码成功 → 清 token → 跳 `/login`（提示"请重新登录"）

### 4.2 api/index.ts 新增函数

`getMyProfile` / `updateMyProfile` / `changePassword` / `getMyComments` / `deleteComment` / `toggleFavorite` / `getMyFavorites`

### 4.3 路由守卫（router/index.ts）

`/profile` 加入 `meta: { requiresAuth: true }`，`beforeEach` 里检查 `isLoggedIn`（参照现有 login/register 守卫逻辑）

**已核对的现状**：守卫已存在（登录用户访问 login/register 跳 `/`）；在 `beforeEach` 里加分支：`if (to.meta.requiresAuth && !isLoggedIn.value) next('/login')`；路由对象加 `/profile`（component 懒加载 `../views/ProfilePage.vue`）。

### 检查方式

- 浏览器登录后访问 `/profile`：资料显示正确
- 改 MBTI 保存 → 刷新后仍显示新值
- 改密码 → 被踢回登录页，旧密码无法登录
- 未登录直接访问 `/profile` → 跳登录页

---

## 第 5 步：前端 · Tab + 收藏 + 首页联动 + 导航入口

### 5.1 ProfilePage 两个 Tab（书评 / 收藏）

- 书评 Tab：列表渲染 + 删除（确认后调 `deleteComment`，本地移除）
- 收藏 Tab：卡片网格，点击进 `/books/:id`；空态提示
- Tab 切换懒加载（切换时再请求）

### 5.2 BookDetailPage 收藏按钮

- 标题旁爱心按钮：`GET /books/{id}` 返回 `is_favorited` 初始化
- 点击 → `toggleFavorite` → 本地翻转 + 轻提示（toast 或按钮动画）
- 未登录点击 → 跳登录

### 5.3 HomePage MBTI 联动

- 若 `localStorage.user.mbti_type_id` 存在 → 对应类型卡片加高亮边框 + 文案"你的类型"
- 点击高亮卡片 → 进入对应 `/types/xxx`（现有行为，无需改跳转逻辑）

### 5.4 App.vue 导航入口

- 登录后：显示用户默认头像（小圆），点击 → `/profile`；旁边保留退出按钮
- 未登录：保持"登录/注册"链接

**已核对的现状**（App.vue 22-30 行）：登录态当前显示 `{{ user?.username }}` 文本 + 退出按钮 —— 把用户名文本替换为可点击的头像入口（`router-link to="/profile"` 包一个首字母圆形头像），退出按钮保留。

### 检查方式（完整回归）

1. 登录 → 导航栏出现头像 → 进 `/profile`
2. 设置 MBTI → 回首页该类型高亮
3. 详情页收藏 → 个人中心"收藏"Tab 出现该书 → 取消收藏 → Tab 消失
4. 发一条书评 → "我的书评"Tab 出现 → 删除 → 消失且详情页评论数减 1
5. 退出登录 → 导航恢复登录/注册；直接访问 `/profile` 被拦

---

## 第 6 步：验证收尾

- [ ] `vue-tsc --noEmit` 零错误
- [ ] 后端接口全链路 curl 冒烟（对照各步验收标准）
- [ ] 更新 `docs/test-report-2026-07-31.md` 追加本功能测试记录
- [ ] 提交（沿用分域 commit 风格）

## 遇到问题时的求助姿势

把以下信息发我，我帮你定位（只诊断不代写）：
1. 报错原文 + 涉及文件/行号
2. 你尝试过的排查
3. 接口返回的完整 JSON / 浏览器 console 截图
