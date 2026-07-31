# 书籍详情页 + 书评社区 · 手搓实施清单

> 模式：指导手搓。按顺序完成 2-6 步，每步写完后跑验收命令，全部完成后由助手做端到端验证。
> 第 1 步（数据库迁移）已完成：`comments.book_id` 已加（NOT NULL + 外键），备份表 `comments_backup` 已留存。

---

## 第 2 步：后端 Model + Schema

### ① `backend/app/models/comment.py`

- 新增：`book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))`
- 修改：`recommendation_id` 改 `nullable=True`，注释"兼容旧数据，新评论不再使用"

### ② `backend/app/schemas/comment.py`

- `CommentCreateRequest`：`recommendation_id: int` → `book_id: int`
- `CommentResponse`：`recommendation_id: int` → `book_id: int`

### ③ `backend/app/schemas/book.py`（追加两个类）

```python
class RecommendedTypeInfo(BaseModel):
    code: str
    name: str


class BookDetailResponse(BaseModel):
    id: int
    title: str
    author: str
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    recommended_types: list[RecommendedTypeInfo] = []
    comment_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
```

**验收**：`uv run python -c "from app.models import Comment; from app.schemas.comment import CommentCreateRequest, CommentResponse; from app.schemas.book import BookDetailResponse; print('OK')"`

---

## 第 3 步：路由改造

### ① `backend/app/routers/comments.py`

`create_comment`：`req.recommendation_id` → `req.book_id`；`Comment(...)` 构造用 `book_id=req.book_id`（不传 recommendation_id）；响应 `book_id=comment.book_id`。

`list_comments` 改路径与查询：

```python
@router.get("/book/{book_id}", response_model=ApiListResponse[CommentResponse])
async def list_book_comments(book_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Comment, User)
        .join(User, Comment.user_id == User.id)
        .where(Comment.book_id == book_id, Comment.is_hidden == False)
        .order_by(Comment.created_at.asc())
    )
    rows = result.all()

    data = []
    for c, u in rows:
        data.append(CommentResponse(
            id=c.id,
            user_id=c.user_id,
            username=u.username,
            book_id=c.book_id,
            parent_id=c.parent_id,
            content=c.content,
            likes_count=c.likes_count,
            is_edited=c.is_edited,
            created_at=c.created_at,
        ))
    return ApiListResponse(data=data, total=len(data))
```

`toggle_like` 不变。

### ② `backend/app/routers/books.py`（新增详情接口）

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Recommendation, MbtiType, Comment
from app.schemas import ApiResponse, BookResponse, BookDetailResponse, RecommendedTypeInfo


@router.get("/{book_id}/detail", response_model=ApiResponse[BookDetailResponse])
async def get_book_detail(book_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="未找到书目")

    # 被哪些 MBTI 类型推荐（去重）
    type_rows = await session.execute(
        select(MbtiType.code, MbtiType.name)
        .join(Recommendation, Recommendation.mbti_type_id == MbtiType.id)
        .where(Recommendation.book_id == book_id)
        .distinct()
    )
    recommended_types = [RecommendedTypeInfo(code=code, name=name) for code, name in type_rows.all()]

    # 评论数
    comment_count = (await session.execute(
        select(func.count()).select_from(Comment).where(Comment.book_id == book_id)
    )).scalar()

    detail = BookDetailResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        cover_url=book.cover_url,
        description=book.description,
        genre=book.genre,
        recommended_types=recommended_types,
        comment_count=comment_count,
        created_at=book.created_at,
    )
    return ApiResponse(data=detail)
```

**验收**：`uv run python -c "from app.routers import comments, books; print('OK')"`

---

## 第 4 步：`frontend/src/api/index.ts` 追加

```typescript
// 书籍详情接口
export async function getBookDetail(bookId: number) {
    const res = await api.get(`/books/${bookId}/detail`)
    return res.data
}

// 书评接口（挂书）
export async function getBookComments(bookId: number) {
    const res = await api.get(`/comments/book/${bookId}`)
    return res.data
}

export async function createComment(payload: { book_id: number; content: string; parent_id?: number | null }) {
    const res = await api.post('/comments', payload)
    return res.data
}

export async function toggleCommentLike(commentId: number) {
    const res = await api.post(`/comments/${commentId}/like`)
    return res.data
}
```

---

## 第 5 步：新建 `frontend/src/views/BookDetailPage.vue`

**结构**（Tailwind 风格对齐 TypeDetailPage）：
1. 返回按钮
2. 书籍信息卡片：封面大图（`proxyUrl` 代理）+ 书名/作者/题材 + 简介 + 「被推荐给以下 MBTI 类型」chips（`router-link` → `/types/{code}`）
3. 书评区：标题+评论数、未登录提示（`/login` 链接）、发表框（登录后）、评论列表（头像首字/用户名/timeAgo/内容/点赞）

**script 要点**：
- `import { getBookDetail, getBookComments, createComment, toggleCommentLike } from '../api'`
- `import apiConfig from '../api/config'` + `proxyUrl()`（同 TypeDetailPage）
- `import { useAuth } from '../composables/useAuth'` → `isLoggedIn`
- `onMounted` 并行拉 `getBookDetail(bookId)` + `getBookComments(bookId)`
- `submitComment()` → `createComment({ book_id, content })`，成功后 `comments.push(res.data)`
- `toggleLike()` → `toggleCommentLike(comment.id)`
- 完整代码模板见助手会话消息（可让助手重新提供）

---

## 第 6 步：路由 + TypeDetailPage 改造

### ① `frontend/src/router/index.ts` 加路由

```typescript
{
    path: "/books/:id",
    name: "book-detail",
    component: () => import ('../views/BookDetailPage.vue'),
},
```

### ② `frontend/src/views/TypeDetailPage.vue`

**script 删除**（评论区逻辑）：
- `import api from '../api'`（具名 import 保留）
- `import { useAuth }` + `isLoggedIn`
- `activeRecId` computed、`comments/commentLoading/commentText/submitting/likingId` refs
- `timeAgo`、`fetchComments`、`submitComment`、`toggleLike`
- `onMounted`/`handleGenerate` 中的 `await fetchComments()`
- 保留 `apiConfig` import（`proxyUrl` 使用）

**template**：
- 删除整块评论区（`<!-- 评论区 -->` 起始的 div）
- 封面图外包 `<router-link :to="\`/books/${item.book.id}\`">`
- 书名同理包 `router-link`（hover 加下划线）

**验收**：`npx vue-tsc --noEmit` 零错误

---

## 第 7 步：端到端验证（助手执行）

- 后端接口冒烟（detail、comments/book）
- 前端 `vue-tsc` + `vite build`
- Playwright 实测：类型页 → 点击书卡 → 详情页 → 发评论 → 点赞
