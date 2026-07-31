import axios from 'axios'
import apiConfig from './config'

const api = axios.create(apiConfig)

// 401 全局处理：token 失效/被拒时清理登录态并跳转登录页。
// 排除登录/注册端点本身（它们返回 401 是正常业务逻辑，不应跳转）
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (
            err.response?.status === 401 &&
            !String(err.config?.url || '').includes('/auth/login') &&
            !String(err.config?.url || '').includes('/auth/register')
        ) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            delete api.defaults.headers.common['Authorization']
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
        }
        return Promise.reject(err)
    }
)

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

// 个人中心接口
export async function getMyProfile() {
    const res = await api.get('/users/me')
    return res.data
}

export async function updateMyProfile(payload: { username?: string; avatar_url?: string; mbti_type_id?: number | null }) {
    const res = await api.put('/users/me', payload)
    return res.data
}

export async function changePassword(payload: { old_password: string; new_password: string }) {
    const res = await api.put('/users/me/password', payload)
    return res.data
}

export async function getMyComments() {
    const res = await api.get('/users/me/comments')
    return res.data
}

export async function deleteComment(commentId: number) {
    const res = await api.delete(`/comments/${commentId}`)
    return res.data
}

export async function toggleFavorite(bookId: number) {
    const res = await api.post(`/users/me/favorites/${bookId}`)
    return res.data
}

export async function getMyFavorites() {
    const res = await api.get('/users/me/favorites')
    return res.data
}

// 系统公告接口
export async function getUnackedAnnouncements() {
    const res = await api.get('/announcements/unacked')
    return res.data
}

export async function ackAnnouncement(announcementId: number) {
    const res = await api.post(`/announcements/${announcementId}/ack`)
    return res.data
}

// 通知接口
export async function getNotifications(page = 1, pageSize = 20) {
    const res = await api.get('/notifications', { params: { page, page_size: pageSize } })
    return res.data
}

export async function getUnreadCount() {
    const res = await api.get('/notifications/unread-count')
    return res.data
}

export async function markNotificationRead(notificationId: number) {
    const res = await api.post(`/notifications/${notificationId}/read`)
    return res.data
}

export async function markAllNotificationsRead() {
    const res = await api.post('/notifications/read-all')
    return res.data
}

// 管理后台接口（仅 admin，后端 get_current_admin 保护）
export async function publishAnnouncement(payload: { title: string; content: string }) {
    const res = await api.post('/announcements', payload)
    return res.data
}

export async function getAnnouncementList(page = 1, pageSize = 20) {
    const res = await api.get('/announcements', { params: { page, page_size: pageSize } })
    return res.data
}

export async function deactivateAnnouncement(announcementId: number) {
    const res = await api.delete(`/announcements/${announcementId}`)
    return res.data
}

export async function getUsers(page = 1, pageSize = 20) {
    const res = await api.get('/users', { params: { page, page_size: pageSize } })
    return res.data
}

export async function sendAdminMessage(userId: number, content: string) {
    const res = await api.post(`/notifications/to/${userId}`, { content })
    return res.data
}

// 密码重置接口
export async function forgotPassword(email: string) {
    const res = await api.post('/auth/password/forgot', { email })
    return res.data
}

export async function resetPassword(token: string, new_password: string) {
    const res = await api.post('/auth/password/reset', { token, new_password })
    return res.data
}

// 管理后台：管理员直接重置指定用户密码
export async function adminResetPassword(userId: number, new_password: string) {
    const res = await api.put(`/users/${userId}/password`, { new_password })
    return res.data
}

export default api
