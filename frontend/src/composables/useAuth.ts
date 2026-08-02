import { ref, computed } from 'vue'
import api from '../api'

const token = ref(localStorage.getItem('token') || '')

let _user: any = null
try {
    _user = JSON.parse(localStorage.getItem('user') || 'null')
} catch { /* ignore */ }
const currentUser = ref<any>(_user)

// Restore auth header on module load
if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
}

export function useAuth() {
    const isLoggedIn = computed(() => !!token.value)

    async function login(username: string, password: string) {
        const res = await api.post('/auth/login', { username, password })
        const d = res.data.data
        token.value = d.access_token
        currentUser.value = d.user
        localStorage.setItem('token', d.access_token)
        localStorage.setItem('user', JSON.stringify(d.user))
        api.defaults.headers.common['Authorization'] = `Bearer ${d.access_token}`
    }

    async function register(username: string, email: string, password: string) {
        const res = await api.post('/auth/register', { username, email, password })
        const d = res.data.data
        token.value = d.access_token
        currentUser.value = d.user
        localStorage.setItem('token', d.access_token)
        localStorage.setItem('user', JSON.stringify(d.user))
        api.defaults.headers.common['Authorization'] = `Bearer ${d.access_token}`
    }

    function logout() {
        token.value = ''
        currentUser.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        delete api.defaults.headers.common['Authorization']
    }

    // 合并补丁到当前登录用户并写回 localStorage（内存 + 持久化同步）
    function updateUser(patch: Partial<any>) {
        currentUser.value = { ...(currentUser.value || {}), ...patch }
        localStorage.setItem('user', JSON.stringify(currentUser.value))
    }

    return { token, user: currentUser, isLoggedIn, login, register, logout, updateUser }
}
