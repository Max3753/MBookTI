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
3. 未提交改动：`password.py`、`fix_comments_recommendation_nullable.py`（待确认后 commit）
