<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getMbtiType, getRecommendations, aiGenerate } from '../api'
import apiConfig from '../api/config'
import { t } from '../composables/useI18n'

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
                <!--封面图：有 URL 显示图片；加载失败时隐藏；无 URL 显示展位块；点击进书籍详情页-->
                <router-link :to="`/books/${item.book.id}`" class="shrink-0">
                    <img
                        v-if="item.book.cover_url && !item.coverFailed"
                        :src="proxyUrl(item.book.cover_url)"
                        :alt="item.book.title"
                        class="w-20 h-28 object-cover rounded-lg shrink-0 hover:opacity-90 transition-opacity duration-200"
                        @error="item.coverFailed = true"
                    >
                    <div
                        v-else
                        class="w-20 h-28 shrink-0 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-2xl font-bold text-indigo-500 dark:text-indigo-400"
                    >
                        {{ (item.book.title || '书').charAt(0) }}
                    </div>
                </router-link>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <router-link
                            :to="`/books/${item.book.id}`"
                            class="hover:underline"
                        >
                            <h3 class="font-semibold text-gray-800 dark:text-gray-100 text-lg">{{ item.book.title }}</h3>
                        </router-link>
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

    </div>
    </div>
</template>

<style scoped>
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
