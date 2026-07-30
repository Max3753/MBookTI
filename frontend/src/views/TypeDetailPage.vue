<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getMbtiType, getRecommendations, aiGenerate } from '../api'
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
        recommendations.value = recRes.data || []
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
</script>

<template>
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
        <div class="h-36 bg-gray-100 dark:bg-gray-800 rounded-2xl"></div>
        <div class="h-36 bg-gray-100 dark:bg-gray-800 rounded-2xl"></div>
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
    </div>
</template>

<style scoped>
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
