<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getMbtiType, getRecommendations, aiGenerate } from '../api'
import api from '../api'
import apiConfig from '../api/config'
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const code = route.params.code as string

const mbtiType = ref<any>(null)
const recommendations = ref<any[]>([])
const loading = ref(true)
const generating = ref(false)
const error = ref('')

onMounted(async () => {
    try {
        const [typeRes, recRes] = await Promise.all([
            getMbtiType(code),
            getRecommendations(code),
        ])
        mbtiType.value = typeRes.data
        // getRecommendations 返回 {data: {items: [...], mbti_type: {...}}, message: "success"}
        recommendations.value = recRes.data?.items || []
        // 评论依赖 activeRecId（推荐列表第一条的 id），必须在 recommendations 赋值后拉取
        await fetchComments()
    } catch (e) {
        error.value = t.load_failed
    } finally {
        loading.value = false
    }
})

async function handleGenerate() {
    generating.value = true
    error.value = ''
    try {
        const res = await aiGenerate(code)
        recommendations.value = res.data || []
        // 新生成的推荐有了 id，评论区随之加载
        await fetchComments()
    } catch (e: any) {
        error.value = e.response?.data?.detail || t.generate_failed
    } finally {
        generating.value = false
    }
}

function getImage(code: string): string {
    try {
        return new URL(`../resources/${code.toLowerCase()}.png`, import.meta.url).href
    } catch {
        return ''
    }
}

// 豆瓣图床防盗链：浏览器直连带 localhost Referer 会被 403，改走后端代理
function proxyUrl(url: string): string {
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}

// ---- 评论 ----
const comments = ref<any[]>([])
const commentLoading = ref(false)
const commentText = ref('')
const submitting = ref(false)
const likingId = ref<number | null>(null)

const { isLoggedIn } = useAuth()
const activeRecId = computed(() => recommendations.value[0]?.id || null)

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

async function fetchComments() {
    if (!activeRecId.value) return
    commentLoading.value = true
    try {
        const res = await api.get(`/comments/recommendation/${activeRecId.value}`)
        comments.value = res.data.data || []
    } catch {
        comments.value = []
    } finally {
        commentLoading.value = false
    }
}

async function submitComment() {
    if (!isLoggedIn.value || !commentText.value.trim() || !activeRecId.value) return
    submitting.value = true
    try {
        const res = await api.post('/comments', {
            recommendation_id: activeRecId.value,
            content: commentText.value.trim(),
        })
        comments.value.unshift(res.data.data)
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
        const res = await api.post(`/comments/${comment.id}/like`)
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
    <!-- 返回按钮（始终可见） -->
    <button
      @click="$router.push('/')"
      class="mb-4 flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors duration-200 cursor-pointer"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      返回
    </button>

    <!-- 骨架屏加载 -->
    <div v-if="loading" class="animate-pulse space-y-6">
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <div class="flex gap-3 items-center mb-4">
                <div class="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                <div class="h-6 w-20 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                <div class="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            </div>
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            <div class="flex gap-2 mt-4">
                <div class="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                <div class="h-6 w-20 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                <div class="h-6 w-14 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
            </div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <div class="flex gap-3 items-start mb-3">
                <div class="w-1.5 h-16 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                <div class="flex-1">
                    <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-3"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3 mt-1"></div>
                </div>
            </div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <div class="flex gap-3 items-start mb-3">
                <div class="w-1.5 h-16 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                <div class="flex-1">
                    <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-2/3 mb-2"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/5 mb-3"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mt-1"></div>
                </div>
            </div>
        </div>
    </div>

    <div v-else-if="error && !mbtiType" class="text-center py-20 text-red-400">{{ error }}</div>

    <div v-else>

        <!-- MBTI 类型头部 -->
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 mb-6">
            <div class="flex items-center gap-4 mb-3">
                <div class="w-16 h-16 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center overflow-hidden shrink-0">
                    <img
                    :src="getImage(code)"
                    :alt="code"
                    class="w-full h-full object-cover"
                    @error="(e: any) => e.target.style.display = 'none'"
                    >
                </div>
                <div class="flex items-center gap-3 flex-wrap">
                    <span class="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{{ mbtiType?.code }}</span>
                <span class="text-xl text-gray-800 dark:text-gray-100 font-medium">{{ mbtiType?.name }}</span>
                                    <span class="text-sm text-gray-400 dark:text-gray-500 hidden sm:inline">{{ mbtiType?.name_en }}</span>
                </div>
            </div>
            <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{{ mbtiType?.description }}</p>
            <div class="flex flex-wrap gap-2 mt-4">
                <span
                v-for="trait in mbtiType?.traits || []"
                :key="trait"
                class="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs rounded-full font-medium">
                {{ trait }}
                </span>
            </div>
        </div>

        <!-- 推荐书单 -->
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{{ t.recommend_title }}</h2>
            <button
            v-if="recommendations.length == 0"
            @click="handleGenerate"
            :disabled="generating"
            class="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-all duration-200 shadow-sm hover:shadow-md active:scale-95 cursor-pointer">
            <span v-if="generating" class="flex items-center gap-2">
                <div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                {{ t.generating }}
            </span>
            <span v-else>{{ t.ai_generate }}</span>
            </button>
        </div>

        <div v-if="error" class="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm rounded-xl px-4 py-3 mb-4">{{ error }}</div>

        <!-- 推荐列表 -->
        <div v-if="recommendations.length > 0" class="space-y-4">
            <div
            v-for="(item, index) in recommendations"
            :key="item.id"
            class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-all duration-300"
            :style="{ animationDelay: `${index * 0.1}s` }"
            style="animation: fadeInUp 0.5s ease-out both"
            >
            <div class="flex items-start gap-4">
                <div class="w-1.5 h-full min-h-[4rem] rounded-full bg-indigo-100 dark:bg-indigo-800 shrink-0 mt-1"></div>
                <!--封面图：有 URL 显示图片；加载失败时隐藏；无 URL 显示展位块-->
                <img
                    v-if="item.book.cover_url && !item.coverFailed"
                    :src="proxyUrl(item.book.cover_url)"
                    :alt="item.book.title"
                    class="w-20 h-28 object-cover rounded-lg shrink-0"
                    @error="item.coverFailed = true"
                >
                <div
                    v-else
                    class="w-20 h-28 shrink-0 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-2xl font-bold text-indigo-500 dark:text-indigo-400"
                >
                    {{ (item.book.title || '书').charAt(0) }}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <h3 class="font-semibold text-gray-800 dark:text-gray-100 text-lg">{{ item.book.title }}</h3>
                        <span v-if="item.relevance_score" class="text-xs bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium shrink-0">
                            {{ item.relevance_score }}{{ t.score }}
                        </span>
                    </div>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ item.book.author }}</p>
                    <p v-if="item.book.genre" class="text-xs text-indigo-500 dark:text-indigo-400 mt-2 inline-block px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/30 rounded-full">
                        {{ item.book.genre }}
                    </p>
                    <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                        <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed italic">
                            "{{ item.reasoning }}"
                        </p>
                    </div>
                </div>
            </div>
            </div>
        </div>

        <div v-else-if="!generating" class="text-center py-20">
            <div class="text-5xl mb-4">📖</div>
            <p class="text-gray-400 dark:text-gray-500 text-lg">{{ t.no_recommend }}</p>
            <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">{{ t.no_recommend_desc }}</p>
        </div>

        <!-- 评论区 -->
        <div v-if="recommendations.length > 0" class="mt-10">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">{{ t.comments_title }}</h2>

            <!-- 未登录提示 -->
            <div v-if="!isLoggedIn" class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 text-center">
                <p class="text-gray-400 dark:text-gray-500 text-sm">
                    <router-link to="/login" class="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">{{ t.comments_login }}</router-link>
                </p>
            </div>

            <!-- 评论表单 -->
            <div v-else class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 mb-4">
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

            <!-- 评论列表骨架 -->
            <div v-if="commentLoading" class="animate-pulse space-y-3">
                <div class="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div class="flex items-center gap-3 mb-3">
                        <div class="h-7 w-7 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                        <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                    </div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mt-2"></div>
                </div>
                <div class="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div class="flex items-center gap-3 mb-3">
                        <div class="h-7 w-7 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                        <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-12"></div>
                    </div>
                    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
                </div>
            </div>

            <!-- 评论列表 -->
            <div v-else-if="comments.length > 0" class="space-y-3">
                <div
                v-for="comment in comments"
                :key="comment.id"
                class="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-700 transition-all duration-200"
                >
                    <div class="flex items-start justify-between mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <div class="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-xs font-medium text-indigo-600 dark:text-indigo-400 shrink-0">
                                {{ (comment.username || '?').charAt(0).toUpperCase() }}
                            </div>
                            <span class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{{ comment.username }}</span>
                            <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0">{{ timeAgo(comment.created_at) }}</span>
                            <span v-if="comment.is_edited" class="text-xs text-gray-400 dark:text-gray-500 shrink-0">(已编辑)</span>
                        </div>
                        <button
                        @click="toggleLike(comment)"
                        :disabled="!isLoggedIn || likingId === comment.id"
                        class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer shrink-0 ml-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        :class="comment.liked ? 'bg-red-50 dark:bg-red-900/30 text-red-500 dark:text-red-400' : 'bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600'"
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

<style scoped>
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
