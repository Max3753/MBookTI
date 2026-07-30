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

export default api
