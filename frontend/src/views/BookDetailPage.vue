<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBookDetail, getBookComments, createComment, toggleCommentLike, toggleFavorite } from '../api'
import apiConfig, { resolveAssetUrl } from '../api/config'
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const bookId = Number(route.params.id)

const book = ref<any>(null)
const loading = ref(true)
const error = ref('')

// 收藏
const favoriting = ref(false)

async function toggleFav() {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (favoriting.value) return
    favoriting.value = true
    try {
        const res = await toggleFavorite(bookId)
        book.value.is_favorited = res.data.is_favorited
    } catch {
        // silently fail
    } finally {
        favoriting.value = false
    }
}

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
        // getBookComments 返回 {data: [...], total, message}，commentRes.data 即评论数组
        comments.value = commentRes.data || []
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
        // toggleCommentLike 返回 {data: {liked, likes_count}, message}
        comment.liked = res.data.liked
        comment.likes_count = res.data.likes_count
    } catch {
        // silently fail
    } finally {
        likingId.value = null
    }
}
</script>

<template>
    <div class="newsprint-texture">
    <!-- 返回按钮 -->
    <button
      @click="goBack"
      class="mb-6 flex items-center gap-1.5 np-btn np-btn-ghost px-3 text-sm cursor-pointer"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      <span class="edition-label">返回 · BACK</span>
    </button>

    <!-- 加载骨架：报纸灰块 + 硬边框 -->
    <div v-if="loading" class="animate-pulse space-y-6">
        <div class="np-card p-6">
            <div class="flex gap-4">
                <div class="w-28 h-36 bg-divider border border-ink/10"></div>
                <div class="flex-1 space-y-3">
                    <div class="h-6 w-1/2 bg-divider border border-ink/10"></div>
                    <div class="h-4 w-1/3 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-full bg-divider border border-ink/10"></div>
                    <div class="h-3 w-2/3 bg-divider border border-ink/10"></div>
                </div>
            </div>
        </div>
        <div class="np-card p-6">
            <div class="h-4 w-24 bg-divider border border-ink/10 mb-4"></div>
            <div class="h-3 w-full bg-divider border border-ink/10 mb-2"></div>
            <div class="h-3 w-3/4 bg-divider border border-ink/10"></div>
        </div>
    </div>

    <div v-else-if="error" class="text-center py-20">
        <div class="mx-auto max-w-md np-card px-8 py-10">
            <div class="edition-label text-editorial mb-3">发行中断 · PRESS HALT</div>
            <p class="font-serif text-2xl font-bold text-ink dark:text-paper">{{ error }}</p>
        </div>
    </div>

    <div v-else>
        <!-- 书籍信息：书评版面头条 -->
        <div class="np-card p-6 sm:p-8 mb-8 animate-fade-up">
            <div class="flex flex-col sm:flex-row gap-6 sm:gap-8">
                <!-- 封面 -->
                <div class="shrink-0">
                    <img
                        v-if="book.cover_url"
                        :src="proxyUrl(book.cover_url)"
                        :alt="book.title"
                        class="w-28 h-36 object-cover newsprint-img border border-ink/10"
                    >
                    <div
                        v-else
                        class="w-28 h-36 shrink-0 relative flex items-center justify-center bg-divider border border-ink/10 overflow-hidden"
                    >
                        <span class="halftone absolute inset-0"></span>
                        <span class="relative font-serif text-4xl font-bold text-neutral-500">{{ (book.title || '书').charAt(0) }}</span>
                    </div>
                </div>
                <!-- 基本信息 -->
                <div class="flex-1 min-w-0">
                    <div class="edition-label text-editorial mb-2">书评 · BOOK REVIEW</div>
                    <div class="flex items-start justify-between gap-3">
                        <h1 class="font-serif font-black text-3xl sm:text-4xl leading-tight tracking-tighter text-ink dark:text-paper">{{ book.title }}</h1>
                        <button
                            @click="toggleFav"
                            :disabled="favoriting"
                            class="shrink-0 flex items-center gap-1.5 px-4 py-2 text-xs font-semibold uppercase tracking-widest transition-colors duration-200 cursor-pointer disabled:opacity-50 border"
                            :class="book.is_favorited
                                ? 'border-editorial bg-paper text-editorial hover:bg-editorial hover:text-paper'
                                : 'border-ink bg-transparent text-ink hover:bg-ink hover:text-paper'"
                        >
                            <svg class="w-4 h-4" :fill="book.is_favorited ? 'currentColor' : 'none'" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                            </svg>
                            {{ book.is_favorited ? '已收藏' : '收藏' }}
                        </button>
                    </div>
                    <p class="mt-2 edition-label text-neutral-500">{{ book.author }}</p>
                    <span v-if="book.genre" class="mt-3 inline-block np-badge np-badge-outline">
                        {{ book.genre }}
                    </span>
                    <!-- 被推荐类型 -->
                    <div v-if="book.recommended_types?.length" class="mt-5">
                        <p class="edition-label text-neutral-500 mb-2">被推荐给以下 MBTI 类型</p>
                        <div class="flex flex-wrap gap-2">
                            <router-link
                                v-for="mt in book.recommended_types"
                                :key="mt.code"
                                :to="`/types/${mt.code}`"
                                class="np-badge np-badge-outline transition-colors duration-200 hover:bg-ink hover:text-paper dark:hover:bg-paper dark:hover:text-ink cursor-pointer"
                            >
                                {{ mt.name }}（{{ mt.code }}）
                            </router-link>
                        </div>
                    </div>
                    <p v-if="book.description" class="mt-4 font-serif text-sm sm:text-base text-neutral-600 dark:text-neutral-300 leading-relaxed text-justify">{{ book.description }}</p>
                </div>
            </div>
        </div>

        <!-- 书评区：读者来信 -->
        <div class="np-card p-6 sm:p-8">
            <div class="flex items-baseline justify-between border-b-4 border-ink dark:border-paper pb-2 mb-6">
                <h2 class="font-serif text-2xl font-bold tracking-tight text-ink dark:text-paper">
                    {{ t.comments_title }}
                </h2>
                <span v-if="comments.length" class="edition-label text-neutral-400">共 {{ comments.length }} 篇</span>
            </div>

            <!-- 未登录提示 -->
            <div v-if="!isLoggedIn" class="text-center py-6 border border-ink/10 bg-divider/40">
                <p class="edition-label text-neutral-500">
                    <router-link to="/login" class="np-btn-link cursor-pointer">{{ t.comments_login }}</router-link>
                </p>
            </div>

            <!-- 发表框 -->
            <div v-else class="mb-6">
                <textarea
                    v-model="commentText"
                    :placeholder="t.comments_placeholder"
                    class="np-input resize-none"
                    rows="3"
                ></textarea>
                <div class="flex justify-end mt-3">
                    <button
                        @click="submitComment"
                        :disabled="submitting || !commentText.trim()"
                        class="np-btn np-btn-primary cursor-pointer"
                    >
                        <span v-if="submitting" class="flex items-center gap-2">
                            <div class="animate-spin w-4 h-4 border-2 border-paper border-t-transparent"></div>
                            {{ t.comments_submitting }}
                        </span>
                        <span v-else>{{ t.comments_submit }}</span>
                    </button>
                </div>
            </div>

            <!-- 评论列表：读者来信 -->
            <div v-if="comments.length > 0" class="space-y-4">
                <div
                    v-for="comment in comments"
                    :key="comment.id"
                    class="border border-ink/10 bg-paper p-4 transition-colors duration-200 hover:bg-divider/30"
                >
                    <div class="flex items-start justify-between mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <div class="w-7 h-7 bg-ink text-paper dark:bg-paper dark:text-ink flex items-center justify-center font-mono text-xs font-bold shrink-0 overflow-hidden">
                                <img v-if="comment.avatar_url" :src="resolveAssetUrl(comment.avatar_url)" :alt="comment.username" class="w-full h-full object-cover" />
                                <template v-else>{{ (comment.username || '?').charAt(0).toUpperCase() }}</template>
                            </div>
                            <span class="text-sm font-semibold text-ink dark:text-paper truncate">{{ comment.username }}</span>
                            <span class="edition-label text-neutral-400 shrink-0">{{ timeAgo(comment.created_at) }}</span>
                        </div>
                        <button
                            @click="toggleLike(comment)"
                            :disabled="!isLoggedIn || likingId === comment.id"
                            class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium transition-colors duration-200 cursor-pointer shrink-0 ml-2 disabled:opacity-50 disabled:cursor-not-allowed border"
                            :class="comment.liked
                                ? 'border-editorial bg-paper text-editorial'
                                : 'border-ink bg-transparent text-ink hover:bg-ink hover:text-paper'"
                        >
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/>
                            </svg>
                            <span>{{ comment.likes_count || '' }}</span>
                        </button>
                    </div>
                    <p class="text-sm font-serif text-neutral-600 dark:text-neutral-300 leading-relaxed whitespace-pre-wrap text-justify">{{ comment.content }}</p>
                </div>
            </div>

            <div v-else-if="!commentLoading" class="text-center py-12 border-t border-ink/10 mt-6">
                <p class="edition-label text-neutral-500">{{ t.comments_empty }}</p>
            </div>
        </div>
    </div>
    </div>
</template>
