<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMbtiTypes, getUnackedAnnouncements, ackAnnouncement } from '../api';
import { t } from '../composables/useI18n'
import { useAuth } from '../composables/useAuth'

const router = useRouter();
const { user, isLoggedIn } = useAuth();
const types = ref<any[]>([]);
const loading = ref(true);
const loadError = ref(false);

// 系统公告弹窗
const announcements = ref<any[]>([])
const announcementIndex = ref(0)
const acking = ref(false)

const currentAnnouncement = computed(() => announcements.value[announcementIndex.value] || null)

async function loadAnnouncements() {
    try {
        const res = await getUnackedAnnouncements()
        let list = res.data || []
        if (!isLoggedIn.value) {
            // 未登录：过滤本会话已确认的公告
            const seen = JSON.parse(sessionStorage.getItem('announcement_seen') || '[]')
            list = list.filter((a: any) => !seen.includes(a.id))
        }
        if (list.length > 0) {
            announcements.value = list
            announcementIndex.value = 0
        }
    } catch { /* 公告加载失败不阻塞主页 */ }
}

async function confirmAnnouncement() {
    const ann = currentAnnouncement.value
    if (!ann) return
    acking.value = true
    try {
        if (isLoggedIn.value) {
            await ackAnnouncement(ann.id)
        } else {
            // 未登录：sessionStorage 记录本次会话已确认
            const seen = JSON.parse(sessionStorage.getItem('announcement_seen') || '[]')
            if (!seen.includes(ann.id)) {
                seen.push(ann.id)
                sessionStorage.setItem('announcement_seen', JSON.stringify(seen))
            }
        }
    } catch { /* 确认失败仍关闭当前弹窗 */ }
    acking.value = false
    announcementIndex.value += 1
    if (announcementIndex.value >= announcements.value.length) {
        announcements.value = []
    }
}

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
    loadAnnouncements();
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
            class="group bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm hover:shadow-lg hover:-translate-y-1.5 transition-all duration-300 border border-gray-100 dark:border-gray-700 text-left cursor-pointer flex items-center justify-between relative"
            :class="user?.mbti_type_id === item.id ? 'ring-2 ring-indigo-500 dark:ring-indigo-400' : ''"
            >
            <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                    <div class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ item.code }}</div>
                    <span v-if="user?.mbti_type_id === item.id"
                        class="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-indigo-600 text-white leading-none">
                        我的
                    </span>
                </div>
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

        <!-- 系统公告弹窗（必须保持在单根节点内部，否则 Transition 动画失效导致路由切换后新页面不渲染） -->
        <div v-if="currentAnnouncement" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="announcements = []">
            <div class="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
                    <div class="flex items-center gap-2">
                        <svg class="w-5 h-5 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
                        </svg>
                        <span class="font-bold text-gray-800 dark:text-gray-100">系统公告</span>
                        <span v-if="announcements.length > 1" class="text-xs text-gray-400">{{ announcementIndex + 1 }}/{{ announcements.length }}</span>
                    </div>
                </div>
                <div class="px-6 py-5">
                    <h3 class="text-lg font-bold text-gray-800 dark:text-gray-100 mb-2">{{ currentAnnouncement.title }}</h3>
                    <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">{{ currentAnnouncement.content }}</p>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 dark:border-gray-700 flex justify-end">
                    <button
                        @click="confirmAnnouncement"
                        :disabled="acking"
                        class="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl transition-all duration-200 disabled:opacity-50 cursor-pointer"
                    >
                        {{ acking ? '确认中...' : '我知道了' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
