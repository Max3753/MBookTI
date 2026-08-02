<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getMbtiType, getRecommendations, aiGenerate } from '../api'
import apiConfig from '../api/config'
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const code = route.params.code as string
const { isLoggedIn, user } = useAuth()

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
    } catch (e) {
        error.value = t.load_failed
    } finally {
        loading.value = false
    }
})

async function handleGenerate() {
    if (!isLoggedIn.value) {
        window.location.href = '/login'
        return
    }
    generating.value = true
    error.value = ''
    try {
        // AI 生成（后端入库）；生成成功后重新拉取完整推荐列表，
        // 保证数据形状与 getRecommendations 一致（含 book.id/cover_url 等）
        await aiGenerate(code)
        const recRes = await getRecommendations(code)
        recommendations.value = recRes.data?.items || []
    } catch (e: any) {
        error.value = e.response?.data?.detail || t.generate_failed
    } finally {
        generating.value = false
    }
}

function getImage(code: string): string {
    try {
        return new URL(`../resources/mbti_img/${code.toLowerCase()}.png`, import.meta.url).href
    } catch {
        return ''
    }
}

// 豆瓣图床防盗链：浏览器直连带 localhost Referer 会被 403，改走后端代理
function proxyUrl(url: string): string {
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}
</script>

<template>
    <div class="newsprint-texture">
    <!-- 返回按钮（始终可见） -->
    <button
      @click="$router.push('/')"
      class="mb-6 flex items-center gap-1.5 np-btn np-btn-ghost px-3 text-sm cursor-pointer"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      <span class="edition-label">返回 · BACK</span>
    </button>

    <!-- 骨架屏加载：报纸灰块 + 硬边框 -->
    <div v-if="loading" class="animate-pulse space-y-6">
        <div class="np-card p-6">
            <div class="flex gap-4 items-center mb-6">
                <div class="w-16 h-16 bg-divider border border-ink/10"></div>
                <div class="flex-1 space-y-3">
                    <div class="h-8 w-2/3 bg-divider border border-ink/10"></div>
                    <div class="h-4 w-1/3 bg-divider border border-ink/10"></div>
                </div>
            </div>
            <div class="h-4 w-3/4 bg-divider border border-ink/10"></div>
            <div class="flex gap-2 mt-5">
                <div class="h-6 w-16 bg-divider border border-ink/10"></div>
                <div class="h-6 w-20 bg-divider border border-ink/10"></div>
                <div class="h-6 w-14 bg-divider border border-ink/10"></div>
            </div>
        </div>
        <div class="np-card p-6">
            <div class="flex gap-4 items-start">
                <div class="w-1.5 h-20 bg-editorial shrink-0"></div>
                <div class="flex-1 space-y-3">
                    <div class="h-5 w-1/2 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-1/4 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-full bg-divider border border-ink/10"></div>
                    <div class="h-3 w-2/3 bg-divider border border-ink/10"></div>
                </div>
            </div>
        </div>
        <div class="np-card p-6">
            <div class="flex gap-4 items-start">
                <div class="w-1.5 h-20 bg-editorial shrink-0"></div>
                <div class="flex-1 space-y-3">
                    <div class="h-5 w-2/3 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-1/5 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-3/4 bg-divider border border-ink/10"></div>
                    <div class="h-3 w-1/2 bg-divider border border-ink/10"></div>
                </div>
            </div>
        </div>
    </div>

    <div v-else-if="error && !mbtiType" class="text-center py-20">
        <div class="mx-auto max-w-md np-card px-8 py-10">
            <div class="edition-label text-editorial mb-3">发行中断 · PRESS HALT</div>
            <p class="font-serif text-2xl font-bold text-ink dark:text-paper">{{ error }}</p>
        </div>
    </div>

    <div v-else>

        <!-- 报头：人物专访版 -->
        <div class="np-card p-6 sm:p-8 mb-8 animate-fade-up">
            <div class="flex flex-col sm:flex-row sm:items-start gap-6">
                <div class="w-20 h-20 shrink-0 border border-ink dark:border-paper bg-divider flex items-center justify-center overflow-hidden">
                    <img
                    :src="getImage(code)"
                    :alt="code"
                    class="w-full h-full object-cover"
                    :class="user?.mbti_type_id === mbtiType?.id ? '' : 'newsprint-img'"
                    @error="(e: any) => e.target.style.display = 'none'"
                    >
                </div>
                <div class="flex-1 min-w-0">
                    <div class="edition-label text-editorial mb-2">人物专访 · PERSONALITY PROFILE</div>
                    <div class="flex items-baseline gap-4 flex-wrap">
                        <span class="font-serif font-black text-6xl sm:text-7xl leading-none tracking-tighter text-ink dark:text-paper">{{ mbtiType?.code }}</span>
                        <span class="font-serif text-2xl sm:text-3xl font-bold text-ink dark:text-paper">{{ mbtiType?.name }}</span>
                        <span class="edition-label text-neutral-400 hidden sm:inline">{{ mbtiType?.name_en }}</span>
                    </div>
                    <p class="mt-4 font-serif text-sm sm:text-base text-neutral-600 dark:text-neutral-300 leading-relaxed text-justify">{{ mbtiType?.description }}</p>
                    <div class="flex flex-wrap gap-2 mt-5 border-t border-ink dark:border-paper pt-4">
                        <span
                        v-for="trait in mbtiType?.traits || []"
                        :key="trait"
                        class="np-badge np-badge-outline">
                        {{ trait }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 推荐书单：书评版面 -->
        <div class="mb-6 animate-fade-up">
            <h2 class="np-section-title">{{ t.recommend_title }}</h2>
            <div class="flex justify-end">
                <button
                @click="handleGenerate"
                :disabled="generating"
                class="np-btn np-btn-primary cursor-pointer">
                <span v-if="generating" class="flex items-center gap-2">
                    <div class="animate-spin w-4 h-4 border-2 border-paper border-t-transparent"></div>
                    {{ t.generating }}
                </span>
                <span v-else>{{ t.ai_generate }}</span>
                </button>
            </div>
        </div>

        <div v-if="error" class="border border-editorial bg-paper text-editorial text-sm px-4 py-3 mb-6 flex items-center gap-3">
            <span class="np-badge np-badge-editorial leading-none">号外</span>
            <span>{{ error }}</span>
        </div>

        <!-- 推荐列表：书评条目 -->
        <div v-if="recommendations.length > 0" class="space-y-6">
            <div
            v-for="(item, index) in recommendations"
            :key="item.id"
            class="np-card p-6 np-card-hover"
            :style="{ animationDelay: `${index * 0.1}s` }"
            style="animation: fadeInUp 0.5s ease-out both"
            >
            <div class="flex items-start gap-5">
                <div class="hidden sm:flex w-10 shrink-0 flex-col items-center pt-1">
                    <span class="font-serif font-black text-3xl leading-none text-editorial">{{ String(index + 1).padStart(2, '0') }}</span>
                    <span class="edition-label text-neutral-400 mt-1">BOOK</span>
                </div>
                <!--封面图：有 URL 显示图片；加载失败时隐藏；无 URL 显示展位块；点击进书籍详情页-->
                <router-link :to="`/books/${item.book.id}`" class="shrink-0">
                    <img
                        v-if="item.book.cover_url && !item.coverFailed"
                        :src="proxyUrl(item.book.cover_url)"
                        :alt="item.book.title"
                        class="w-20 h-28 object-cover shrink-0 hover:opacity-90 transition-opacity duration-200 newsprint-img border border-ink/10"
                        @error="item.coverFailed = true"
                    >
                    <div
                        v-else
                        class="w-20 h-28 shrink-0 relative flex items-center justify-center bg-divider border border-ink/10 overflow-hidden"
                    >
                        <span class="halftone absolute inset-0"></span>
                        <span class="relative font-serif text-3xl font-bold text-neutral-500">{{ (item.book.title || '书').charAt(0) }}</span>
                    </div>
                </router-link>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <router-link
                            :to="`/books/${item.book.id}`"
                            class="hover:underline decoration-editorial decoration-2 underline-offset-4"
                        >
                            <h3 class="font-serif font-bold text-ink dark:text-paper text-lg">{{ item.book.title }}</h3>
                        </router-link>
                        <span v-if="item.relevance_score" class="np-badge np-badge-editorial leading-none shrink-0">
                            {{ item.relevance_score }}{{ t.score }}
                        </span>
                    </div>
                    <p class="edition-label text-neutral-500">{{ item.book.author }}</p>
                    <p v-if="item.book.genre" class="mt-2 inline-block np-badge np-badge-outline">
                        {{ item.book.genre }}
                    </p>
                    <div class="mt-4 p-4 bg-paper border-l-4 border-editorial">
                        <p class="text-sm font-serif text-neutral-600 dark:text-neutral-300 leading-relaxed italic text-justify">
                            "{{ item.reasoning }}"
                        </p>
                    </div>
                </div>
            </div>
            </div>
        </div>

        <div v-else-if="!generating" class="text-center py-20">
            <div class="mx-auto max-w-md np-card px-8 py-10">
                <div class="edition-label text-editorial mb-3">暂无书评 · NO REVIEWS</div>
                <p class="font-serif text-2xl font-bold text-ink dark:text-paper mb-2">{{ t.no_recommend }}</p>
                <p class="text-sm text-neutral-500">{{ t.no_recommend_desc }}</p>
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
