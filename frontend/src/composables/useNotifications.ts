// 通知未读数共享状态 — 模块级 ref（仿 useAuth 模式）。
// 让 App.vue 导航栏红点与 NotificationsPage 已读操作共享同一数据源，
// 避免"通知已读但导航栏红点要等 30s 轮询才更新"的不同步问题。
import { ref } from 'vue'
import { getUnreadCount } from '../api'
import { useAuth } from './useAuth'

const unread = ref(0)

export function useNotifications() {
    const { isLoggedIn } = useAuth()

    async function refreshUnread() {
        if (!isLoggedIn.value) {
            unread.value = 0
            return
        }
        try {
            const res = await getUnreadCount()
            unread.value = res.data?.unread || 0
        } catch { /* 忽略，保持原值 */ }
    }

    return { unread, refreshUnread }
}
