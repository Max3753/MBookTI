<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
    getBookDetail,
    getBookComments,
    createComment,
    toggleCommentLike,
    toggleFavorite,
    rateBook,
    unrateBook,
} from '../api'
import apiConfig, { resolveAssetUrl } from '../api/config'
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

// 评论数据结构（含回复：parent_id 非空）
interface BookComment {
    id: number
    user_id: number
    username: string
    avatar_url: string | null
    book_id: number
    book_title: string
    book_cover_url: string | null
    parent_id: number | null
    content: string
    likes_count: number
    liked?: boolean
    created_at: string
}

// 扁平列表渲染用节点：标记是否为回复及其父评论（用于缩进与"回复 @xxx"标识）
interface CommentNode {
    comment: BookComment
    isReply: boolean
    parent: BookComment | null
}

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
const comments = ref<BookComment[]>([])
const commentLoading = ref(false)
const commentText = ref('')
const submitting = ref(false)
const likingId = ref<number | null>(null)
const { isLoggedIn } = useAuth()

// 回复：replyToId 为正在展开回复框的评论 id
const replyToId = ref<number | null>(null)
const replyText = ref('')
const replySubmitting = ref(false)

// 评分
const ratingSubmitting = ref(false)
const hoverRating = ref(0)

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

// 评分展示：平均分保留 1 位小数
const avgRatingText = computed(() => {
    const avg = book.value?.avg_rating
    if (avg === null || avg === undefined) return ''
    return Number(avg).toFixed(1)
})

// 星星高亮：悬停预览优先，否则用我的评分
const displayRating = computed(() => hoverRating.value || book.value?.my_rating || 0)

function findCommentById(id: number): BookComment | null {
    return comments.value.find((c) => c.id === id) || null
}

// 组装树形渲染节点：顶层评论 + 其下回复；父级缺失的回复兜底展示
const commentNodes = computed<CommentNode[]>(() => {
    const nodes: CommentNode[] = []
    const seen = new Set<number>()
    for (const c of comments.value) {
        if (!c.parent_id) {
            nodes.push({ comment: c, isReply: false, parent: null })
            seen.add(c.id)
            for (const r of comments.value) {
                if (r.parent_id === c.id) {
                    nodes.push({ comment: r, isReply: true, parent: c })
                    seen.add(r.id)
                }
            }
        }
    }
    // 兜底：父评论被删除等导致未匹配的回复，作为回复展示
    for (const c of comments.value) {
        if (!seen.has(c.id)) {
            nodes.push({
                comment: c,
                isReply: true,
                parent: c.parent_id !== null ? findCommentById(c.parent_id) : null,
            })
        }
    }
    return nodes
})

const replyPlaceholder = computed(() => {
    const parent = replyToId.value !== null ? findCommentById(replyToId.value) : null
    return parent ? `回复 @${parent.username}` : '回复...'
})

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

async function toggleLike(comment: BookComment) {
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

// 回复：点击展开/收起评论下方的回复框（未登录跳转登录页）
function openReply(comment: BookComment) {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    replyToId.value = replyToId.value === comment.id ? null : comment.id
    replyText.value = ''
}

async function submitReply() {
    const parentId = replyToId.value
    if (!parentId || !replyText.value.trim()) return
    replySubmitting.value = true
    try {
        const res = await createComment({
            book_id: bookId,
            content: replyText.value.trim(),
            parent_id: parentId,
        })
        // 追加进扁平数组，渲染时自动嵌套到父评论下方
        comments.value.push(res.data)
        replyToId.value = null
        replyText.value = ''
    } catch {
        // silently fail
    } finally {
        replySubmitting.value = false
    }
}

// 评分：点击星星打分；点击已选中的星星清除评分
async function submitRating(rating: number) {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (ratingSubmitting.value) return
    if (book.value?.my_rating === rating) {
        await removeRating()
        return
    }
    ratingSubmitting.value = true
    try {
        await rateBook(bookId, rating)
        // 重拉详情，保证 avg_rating / rating_count / my_rating 与后端一致
        await reloadBook()
    } catch {
        // silently fail
    } finally {
        ratingSubmitting.value = false
    }
}

async function removeRating() {
    if (!isLoggedIn.value) return
    if (ratingSubmitting.value) return
    ratingSubmitting.value = true
    try {
        await unrateBook(bookId)
        // 删除评分返回 rating:null，统一重拉详情更新评分统计
        await reloadBook()
    } catch {
        // silently fail
    } finally {
        ratingSubmitting.value = false
    }
}

async function reloadBook() {
    const res = await getBookDetail(bookId)
    book.value = res.data
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
                    <!-- 评分：读者评分栏（1-5 星，登录后可评分） -->
                    <div class="mt-5 flex flex-wrap items-center gap-x-3 gap-y-2">
                        <div class="flex items-center gap-1" :title="isLoggedIn ? '点击评分（1-5 星）' : '登录后可评分'">
                            <button
                                v-for="star in 5"
                                :key="star"
                                @click="submitRating(star)"
                                @mouseenter="hoverRating = star"
                                @mouseleave="hoverRating = 0"
                                :disabled="ratingSubmitting"
                                class="text-2xl leading-none transition-transform duration-150 hover:scale-125 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                                :class="star <= displayRating ? 'text-editorial' : 'text-neutral-300 dark:text-neutral-600'"
                            >★</button>
                        </div>
                        <span class="edition-label text-neutral-500 dark:text-neutral-400">
                            <template v-if="book.avg_rating != null && book.rating_count">★ {{ avgRatingText }} · {{ book.rating_count }} 人评分</template>
                            <template v-else>暂无评分</template>
                        </span>
                        <button
                            v-if="book.my_rating"
                            @click="removeRating"
                            :disabled="ratingSubmitting"
                            class="np-btn-link text-xs cursor-pointer disabled:opacity-50"
                        >清除评分</button>
                    </div>
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

            <!-- 评论列表：读者来信（顶层 + 缩进回复树） -->
            <div v-if="comments.length > 0" class="border border-ink/10">
                <div
                    v-for="node in commentNodes"
                    :key="node.comment.id"
                    class="bg-paper border-b border-ink/10 last:border-b-0"
                    :class="node.isReply
                        ? 'ml-6 sm:ml-10 border-l-2 border-ink/15 pl-3 sm:pl-4'
                        : ''"
                >
                    <div class="p-4 transition-colors duration-200 hover:bg-divider/30">
                        <div class="flex items-start justify-between mb-2 gap-2">
                            <div class="flex items-center gap-2 min-w-0">
                                <!-- 头像 + 用户名：点击进入用户主页 -->
                                <router-link
                                    :to="`/users/${node.comment.user_id}`"
                                    class="w-7 h-7 bg-ink text-paper dark:bg-paper dark:text-ink flex items-center justify-center font-mono text-xs font-bold shrink-0 overflow-hidden"
                                >
                                    <img v-if="node.comment.avatar_url" :src="resolveAssetUrl(node.comment.avatar_url)" :alt="node.comment.username" class="w-full h-full object-cover" />
                                    <template v-else>{{ (node.comment.username || '?').charAt(0).toUpperCase() }}</template>
                                </router-link>
                                <router-link
                                    :to="`/users/${node.comment.user_id}`"
                                    class="text-sm font-semibold text-ink dark:text-paper hover:text-editorial transition-colors truncate"
                                >{{ node.comment.username }}</router-link>
                                <span v-if="node.isReply && node.parent" class="np-badge np-badge-outline leading-none shrink-0">
                                    回复 @{{ node.parent.username }}
                                </span>
                                <span class="edition-label text-neutral-400 shrink-0">{{ timeAgo(node.comment.created_at) }}</span>
                            </div>
                            <div class="flex items-center gap-2 shrink-0 ml-2">
                                <button
                                    @click="openReply(node.comment)"
                                    :disabled="!isLoggedIn"
                                    class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium transition-colors duration-200 cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed border"
                                    :class="replyToId === node.comment.id
                                        ? 'border-editorial bg-paper text-editorial'
                                        : 'border-ink bg-transparent text-ink hover:bg-ink hover:text-paper dark:text-paper dark:border-paper dark:hover:bg-paper dark:hover:text-ink'"
                                >
                                    回复
                                </button>
                                <button
                                    @click="toggleLike(node.comment)"
                                    :disabled="!isLoggedIn || likingId === node.comment.id"
                                    class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium transition-colors duration-200 cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed border"
                                    :class="node.comment.liked
                                        ? 'border-editorial bg-paper text-editorial'
                                        : 'border-ink bg-transparent text-ink hover:bg-ink hover:text-paper dark:text-paper dark:border-paper dark:hover:bg-paper dark:hover:text-ink'"
                                >
                                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/>
                                    </svg>
                                    <span>{{ node.comment.likes_count || '' }}</span>
                                </button>
                            </div>
                        </div>
                        <p class="text-sm font-serif text-neutral-600 dark:text-neutral-300 leading-relaxed whitespace-pre-wrap text-justify">{{ node.comment.content }}</p>

                        <!-- 回复框：点击"回复"后展开在对应评论下方 -->
                        <div v-if="replyToId === node.comment.id" class="mt-3 border border-ink/10 bg-divider/40 p-3">
                            <textarea
                                v-model="replyText"
                                :placeholder="replyPlaceholder"
                                class="np-input resize-none"
                                rows="2"
                            ></textarea>
                            <div class="flex justify-end gap-2 mt-2">
                                <button
                                    @click="replyToId = null; replyText = ''"
                                    class="np-btn np-btn-ghost px-3 text-xs cursor-pointer"
                                >取消</button>
                                <button
                                    @click="submitReply"
                                    :disabled="replySubmitting || !replyText.trim()"
                                    class="np-btn np-btn-primary px-3 text-xs cursor-pointer"
                                >
                                    {{ replySubmitting ? '提交中...' : '发表' }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else-if="!commentLoading" class="text-center py-12 border-t border-ink/10 mt-6">
                <p class="edition-label text-neutral-500">{{ t.comments_empty }}</p>
            </div>
        </div>
    </div>
    </div>
</template>
