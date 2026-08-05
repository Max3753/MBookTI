<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api'
import { useNotifications } from '../composables/useNotifications'

const router = useRouter()
const { refreshUnread } = useNotifications()
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
    if (type === 2) return '管理员消息'
    if (type === 3) return '评论被回复'
    if (type === 4) return '被关注'
    return '评论获赞'
}

// 通知类型对应的徽标字
function typeMark(type: number): string {
    if (type === 2) return '管'
    if (type === 3) return '回'
    if (type === 4) return '关'
    return '赞'
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
            refreshUnread()  // 即时更新导航栏红点
        } catch { /* 忽略 */ }
        markingId.value = null
    }
    if (n.related_book_id && n.type !== 4) {
        router.push(`/books/${n.related_book_id}`)
    }
}

async function readAll() {
    try {
        await markAllNotificationsRead()
        notifications.value.forEach((n) => (n.is_read = true))
        refreshUnread()  // 即时清零导航栏红点
    } catch { /* 忽略 */ }
}

onMounted(load)
</script>

<template>
    <div>
        <div class="flex items-end justify-between mb-6">
            <div>
                <p class="edition-label text-neutral-400 dark:text-neutral-500 mb-2">读者来信 · Letters to the Editor</p>
                <h1 class="font-serif text-4xl font-black tracking-tight border-b-4 border-editorial pb-1">通知</h1>
            </div>
            <button
                v-if="notifications.some((n) => !n.is_read)"
                @click="readAll"
                class="np-btn-link text-xs cursor-pointer"
            >
                全部已读
            </button>
        </div>

        <div class="np-card animate-newsprint-in">
            <div v-if="loading" class="p-10 text-center">
                <p class="edition-label text-neutral-400">加载中...</p>
            </div>
            <div v-else-if="notifications.length === 0" class="p-12 text-center">
                <p class="font-serif text-3xl text-neutral-400">暂无通知</p>
                <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-4">书评获赞、被回复、被关注或收到管理员消息时会出现在这里</p>
            </div>
            <div v-else>
                <button
                    v-for="n in notifications"
                    :key="n.id"
                    @click="openNotification(n)"
                    :disabled="markingId === n.id"
                    class="w-full p-4 flex items-start gap-4 text-left transition-colors cursor-pointer disabled:opacity-60 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 border-b border-divider dark:border-paper/40 last:border-b-0"
                >
                    <div class="w-8 h-8 border border-ink dark:border-paper flex items-center justify-center font-mono text-xs shrink-0"
                        :class="n.type === 2 ? 'text-editorial' : 'text-ink dark:text-paper'">
                        {{ typeMark(n.type) }}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <span class="np-badge shrink-0"
                                :class="n.type === 2 ? 'np-badge-editorial' : 'np-badge-outline'">
                                {{ typeText(n.type) }}
                            </span>
                            <span v-if="!n.is_read" class="w-2 h-2 bg-editorial shrink-0"></span>
                            <span class="edition-label text-neutral-400 dark:text-neutral-500 ml-auto shrink-0">{{ timeAgo(n.created_at) }}</span>
                        </div>
                        <p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1.5 leading-relaxed font-body">{{ n.content }}</p>
                        <p v-if="n.related_book_id" class="np-btn-link text-xs mt-1 inline-block">点击查看相关书籍 →</p>
                    </div>
                </button>
            </div>
        </div>
    </div>
</template>
