<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBookDetail, getBookComments, createComment, toggleCommentLike } from '../api'
import apiConfig from '../api/config'
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const bookId = Number(route.params.id)

const book = ref<any>(null)
const loading = ref(true)
const error = ref('')

// 评论
const comments = ref<any[]>([])
const commentLoading = ref(false)
const commentText = ref('')
const submitting = ref(false)
const likingId = ref<number | null>(null)
const { isLoggedIn } = useAuth()

// 豆瓣图床防盗链：走后端代理
function proxyUrl(url: string): string {
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}

// 返回：基于 vue-router 记录的来源路由（history.state.back），
// 不依赖浏览器历史栈（避免多标签/长会话导致 back() 回退异常）
function goBack() {
    const back = (window.history.state?.back as string) || ''
    if (back.startsWith('/') && back !== '/') {
        router.push(back)
    } else {
        router.push('/')
    }
}

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

onMounted(async () => {
    try {
        const [bookRes, commentRes] = await Promise.all([
            getBookDetail(bookId),
            getBookComments(bookId),
        ])
        book.value = bookRes.data
        comments.value = commentRes.data?.data || []
    } catch (e) {
        error.value = t.load_failed
    } finally {
        loading.value = false
        commentLoading.value = false
    }
})

async function submitComment() {
    if (!isLoggedIn.value || !commentText.value.trim()) return
    submitting.value = true
    try {
        const res = await createComment({ book_id: bookId, content: commentText.value.trim() })
        comments.value.push(res.data)
        commentText.value = ''
    } catch {
        // silently fail
    } finally {
        submitting.value = false
    }
}

async function toggleLike(comment: any) {
    if (!isLoggedIn.value || likingId.value) return
    likingId.value = comment.id
    try {
        const res = await toggleCommentLike(comment.id)
        comment.liked = res.data.data.liked
        comment.likes_count = res.data.data.likes_count
    } catch {
        // silently fail
    } finally {
        likingId.value = null
    }
}
</script>

<template>
    <div>
    <!-- 返回按钮 -->
    <button
      @click="goBack"
      class="mb-4 flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors duration-200 cursor-pointer"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      返回
    </button>

    <!-- 加载骨架 -->
    <div v-if="loading" class="animate-pulse space-y-6">
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <div class="flex gap-4">
                <div class="w-28 h-36 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                <div class="flex-1 space-y-3">
                    <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
                </div>
            </div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-4"></div>
            <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
            <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
    </div>

    <div v-else-if="error" class="text-center py-20 text-red-400">{{ error }}</div>

    <div v-else>
        <!-- 书籍信息 -->
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 mb-6">
            <div class="flex flex-col sm:flex-row gap-6">
                <!-- 封面 -->
                <div class="shrink-0">
                    <img
                        v-if="book.cover_url"
                        :src="proxyUrl(book.cover_url)"
                        :alt="book.title"
                        class="w-28 h-36 object-cover rounded-xl shadow-sm"
                    >
                    <div
                        v-else
                        class="w-28 h-36 shrink-0 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-3xl font-bold text-indigo-500 dark:text-indigo-400"
                    >
                        {{ (book.title || '书').charAt(0) }}
                    </div>
                </div>
                <!-- 基本信息 -->
                <div class="flex-1 min-w-0">
                    <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ book.title }}</h1>
                    <p class="mt-1 text-gray-500 dark:text-gray-400">{{ book.author }}</p>
                    <span v-if="book.genre" class="mt-3 inline-block px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs rounded-full font-medium">
                        {{ book.genre }}
                    </span>
                    <!-- 被推荐类型 -->
                    <div v-if="book.recommended_types?.length" class="mt-4">
                        <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">被推荐给以下 MBTI 类型</p>
                        <div class="flex flex-wrap gap-2">
                            <router-link
                                v-for="mt in book.recommended_types"
                                :key="mt.code"
                                :to="`/types/${mt.code}`"
                                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-full font-medium hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors duration-200 cursor-pointer"
                            >
                                {{ mt.name }}（{{ mt.code }}）
                            </router-link>
                        </div>
                    </div>
                    <p v-if="book.description" class="mt-4 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{{ book.description }}</p>
                </div>
            </div>
        </div>

        <!-- 书评区 -->
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
                {{ t.comments_title }}<span v-if="comments.length" class="text-sm text-gray-400 ml-1">（{{ comments.length }}）</span>
            </h2>

            <!-- 未登录提示 -->
            <div v-if="!isLoggedIn" class="text-center py-6 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                <p class="text-gray-400 dark:text-gray-500 text-sm">
                    <router-link to="/login" class="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">{{ t.comments_login }}</router-link>
                </p>
            </div>

            <!-- 发表框 -->
            <div v-else class="mb-4">
                <textarea
                    v-model="commentText"
                    :placeholder="t.comments_placeholder"
                    class="w-full bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-xl p-3 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 resize-none transition-all duration-200"
                    rows="3"
                ></textarea>
                <div class="flex justify-end mt-3">
                    <button
                        @click="submitComment"
                        :disabled="submitting || !commentText.trim()"
                        class="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md active:scale-95 cursor-pointer"
                    >
                        <span v-if="submitting" class="flex items-center gap-2">
                            <div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                            {{ t.comments_submitting }}
                        </span>
                        <span v-else>{{ t.comments_submit }}</span>
                    </button>
                </div>
            </div>

            <!-- 评论列表 -->
            <div v-if="comments.length > 0" class="space-y-3">
                <div
                    v-for="comment in comments"
                    :key="comment.id"
                    class="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 transition-all duration-200"
                >
                    <div class="flex items-start justify-between mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <div class="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-xs font-medium text-indigo-600 dark:text-indigo-400 shrink-0">
                                {{ (comment.username || '?').charAt(0).toUpperCase() }}
                            </div>
                            <span class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{{ comment.username }}</span>
                            <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0">{{ timeAgo(comment.created_at) }}</span>
                        </div>
                        <button
                            @click="toggleLike(comment)"
                            :disabled="!isLoggedIn || likingId === comment.id"
                            class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer shrink-0 ml-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            :class="comment.liked ? 'bg-red-50 dark:bg-red-900/30 text-red-500 dark:text-red-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'"
                        >
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/>
                            </svg>
                            <span>{{ comment.likes_count || '' }}</span>
                        </button>
                    </div>
                    <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">{{ comment.content }}</p>
                </div>
            </div>

            <div v-else-if="!commentLoading" class="text-center py-10">
                <p class="text-gray-400 dark:text-gray-500 text-sm">{{ t.comments_empty }}</p>
            </div>
        </div>
    </div>
    </div>
</template>
