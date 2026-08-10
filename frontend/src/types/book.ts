// 书籍类型定义（对齐后端 schemas/book.py）
// BookResponse（列表/搜索摘要）与 BookDetailResponse（详情页）

export interface RecommendedTypeInfo {
    code: string
    name: string
}

// 对齐后端 BookResponse：列表/搜索卡片展示用
export interface BookSummary {
    id: number
    title: string
    author: string
    isbn?: string | null
    cover_url?: string | null
    description?: string | null
    genre?: string | null
    language: string
    created_at: string
}

// 对齐后端 BookDetailResponse：详情页用
export interface BookDetail extends BookSummary {
    recommended_types: RecommendedTypeInfo[]
    comment_count: number
    is_favorited: boolean
    avg_rating?: number | null
    rating_count: number
    my_rating?: number | null
}

// 搜索结果响应（对齐后端 ApiListResponse[BookResponse]）
export interface SearchResult {
    data: BookSummary[]
    total: number
    message: string
}
