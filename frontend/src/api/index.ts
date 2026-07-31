import axios from 'axios'
import apiConfig from './config'

const api = axios.create(apiConfig)

// MBTI 类型接口
export async function getMbtiTypes() {
    const res = await api.get('/mbti_types')
    return res.data
}

export async function getMbtiType(code: string) {
    const res = await api.get(`/mbti_types/${code}`)
    return res.data
}

// 推荐接口
export async function getRecommendations(mbtiCode: string) {
    const res = await api.get(`/recommendations/mbti/${mbtiCode}`)
    return res.data
}

export async function aiGenerate(mbtiCode: string, count = 5) {
    const res = await api.post('/recommendations/ai-generate', {
        mbti_code: mbtiCode,
        count,
    })
    return res.data
}

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

export default api
