<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMbtiTypes } from '../api';
import { t } from '../composables/useI18n'

const router = useRouter();
const types = ref<any[]>([]);
const loading = ref(true);
const loadError = ref(false);

onMounted(async () => {
    try {
        const res = await getMbtiTypes();
        types.value = res.data;
    } catch (e) {
        loadError.value = true;
        console.error('加载失败', e);
    } finally {
        loading.value = false;
    }
})

function goToType(code: string) {
    router.push(`/types/${code}`)
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
    <div>
        <div class="text-center mb-10">
            <h1 class="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-2">{{ t.home_title }}</h1>
            <p class="text-gray-500 dark:text-gray-400">{{ t.home_desc }}</p>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-20">
            <div class="animate-spin w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto"></div>
            <p class="text-gray-400 mt-4">{{ t.loading }}</p>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="loadError" class="text-center py-20">
            <div class="text-5xl mb-4">😵</div>
            <p class="text-gray-400 mb-3">{{ t.load_failed }}</p>
            <button @click="location.reload()" class="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
                {{ t.retry }}
            </button>
        </div>

        <!-- 数据为空 -->
        <div v-else-if="types.length === 0" class="text-center py-20">
            <div class="text-5xl mb-4">📚</div>
            <p class="text-gray-400">{{ t.no_data }}</p>
        </div>

        <!-- MBTI 卡片 -->
        <div v-else class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <button
            v-for="item in types"
            :key="item.code"
            @click="goToType(item.code)"
            class="group bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm hover:shadow-lg hover:-translate-y-1.5 transition-all duration-300 border border-gray-100 dark:border-gray-700 text-left cursor-pointer flex items-center justify-between"
            >
            <div class="min-w-0 flex-1">
                <div class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ item.code }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{{ item.name }}</div>
                <div class="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">{{ item.name_en }}</div>
            </div>
            <div class="w-16 h-16 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center overflow-hidden shrink-0 ml-3">
                <img
                :src="getImage(item.code)"
                :alt="item.code"
                class="w-full h-full object-cover"
                @error="(e: any) => e.target.style.display = 'none'"
                >
            </div>
            </button>
        </div>
    </div>
</template>
