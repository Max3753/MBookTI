<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api'

const router = useRouter()
const notifications = ref<any[]>([])
const loading = ref(true)
const total = ref(0)
const markingId = ref<number | null>(null)

function timeAgo(dateStr: string): string {
    const now = Date.now()
    const date = new Date(dateStr).getTime()
    const diff = Math.floor((now - date) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    const days = Math.floor(diff / 86400)
    if (days < 30) return `${days}天前`
    return new Date(dateStr).toLocaleDateString('zh-CN')
}

function typeText(type: number): string {
    return type === 2 ? '管理员消息' : '评论获赞'
}

async function load() {
    loading.value = true
    try {
        const res = await getNotifications(1, 50)
        notifications.value = res.data || []
        total.value = res.total || 0
    } catch {
        notifications.value = []
    } finally {
        loading.value = false
    }
}

async function openNotification(n: any) {
    if (!n.is_read) {
        markingId.value = n.id
        try {
            await markNotificationRead(n.id)
            n.is_read = true
        } catch { /* 忽略 */ }
        markingId.value = null
    }
    if (n.related_book_id) {
        router.push(`/books/${n.related_book_id}`)
    }
}

async function readAll() {
    try {
        await markAllNotificationsRead()
        notifications.value.forEach((n) => (n.is_read = true))
    } catch { /* 忽略 */ }
}

onMounted(load)
</script>

<template>
    <div>
        <div class="flex items-center justify-between mb-4">
            <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100">通知</h1>
            <button
                v-if="notifications.some((n) => !n.is_read)"
                @click="readAll"
                class="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
            >
                全部已读
            </button>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
            <div v-if="loading" class="p-10 text-center text-gray-400 text-sm">加载中...</div>
            <div v-else-if="notifications.length === 0" class="p-10 text-center">
                <div class="text-5xl mb-4">🔔</div>
                <p class="text-gray-400">暂无通知</p>
                <p class="text-xs text-gray-400 mt-1">书评获赞或收到管理员消息时会出现在这里</p>
            </div>
            <div v-else class="divide-y divide-gray-100 dark:divide-gray-700">
                <button
                    v-for="n in notifications"
                    :key="n.id"
                    @click="openNotification(n)"
                    :disabled="markingId === n.id"
                    class="w-full p-4 flex items-start gap-3 text-left transition-colors cursor-pointer disabled:opacity-60 hover:bg-gray-50 dark:hover:bg-gray-900/40"
                >
                    <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                        :class="n.type === 2
                            ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300'
                            : 'bg-red-100 dark:bg-red-900/40 text-red-500 dark:text-red-400'">
                        {{ n.type === 2 ? '管' : '赞' }}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 shrink-0">{{ typeText(n.type) }}</span>
                            <span v-if="!n.is_read" class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
                            <span class="text-xs text-gray-400 ml-auto shrink-0">{{ timeAgo(n.created_at) }}</span>
                        </div>
                        <p class="text-sm text-gray-700 dark:text-gray-300 mt-1.5 leading-relaxed">{{ n.content }}</p>
                        <p v-if="n.related_book_id" class="text-xs text-indigo-500 dark:text-indigo-400 mt-1">点击查看相关书籍 →</p>
                    </div>
                </button>
            </div>
        </div>
    </div>
</template>
