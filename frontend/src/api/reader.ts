// 阅读器进度同步接口封装（本地文件阅读，云端仅同步进度，按内容哈希 book_key 关联）
import api from './index'

export interface ReadingRecordItem {
    id: number
    book_key: string
    title: string
    author: string
    format: 'txt' | 'epub' | 'pdf'
    progress: string | null
    progress_total: number | null
    updated_at: string
}

// 保存/更新阅读进度（按 book_key upsert，文件留在本地）
export async function saveReaderProgress(payload: {
    book_key: string
    title: string
    author: string
    format: string
    progress: string | null
    progress_total: number | null
}) {
    const res = await api.put('/reader/progress', payload)
    return res.data as { data: { book_key: string }; message: string }
}

// 读取指定书（按内容哈希 book_key）的进度
export async function getReaderProgress(bookKey: string) {
    const res = await api.get(`/reader/progress/${encodeURIComponent(bookKey)}`)
    return res.data as { data: { position: string | null; total: number | null }; message: string }
}

// 阅读历史（最近阅读在前，含进度与最后阅读时间）
export async function getReadingHistory(page = 1, pageSize = 50) {
    const res = await api.get('/reader/history', { params: { page, page_size: pageSize } })
    return res.data as { data: ReadingRecordItem[]; total: number; message: string }
}

// 删除一条阅读记录（仅云端进度；本地文件不受影响）
export async function deleteReadingRecord(bookKey: string) {
    const res = await api.delete(`/reader/history/${encodeURIComponent(bookKey)}`)
    return res.data as { data: null; message: string }
}
