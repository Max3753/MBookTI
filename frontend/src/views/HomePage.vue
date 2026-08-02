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

const reloadPage = () => window.location.reload()

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

function goToTest() {
    router.push('/test')
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

        <!-- 直觉型 MBTI 测试入口（与类型列表加载无关，始终显示） -->
        <div class="max-w-3xl mx-auto mb-10 animate-fade-up">
            <button
            @click="goToTest"
            class="group relative block w-full overflow-hidden rounded-3xl text-left cursor-pointer select-none
                   bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 animate-gradient-pan
                   shadow-xl shadow-indigo-500/25 transition-all duration-300
                   hover:shadow-2xl hover:shadow-fuchsia-500/40 hover:-translate-y-1
                   dark:shadow-fuchsia-500/30"
            aria-label="开始直觉型 MBTI 测试"
            >
                <!-- 角落呼吸光晕 -->
                <div class="pointer-events-none absolute inset-0" aria-hidden="true">
                    <div class="absolute -top-16 -right-14 w-44 h-44 rounded-full bg-fuchsia-300/40 blur-3xl animate-glow-pulse"></div>
                    <div class="absolute -bottom-20 -left-14 w-56 h-56 rounded-full bg-indigo-300/40 blur-3xl animate-glow-pulse" style="animation-delay: 2s"></div>
                </div>

                <!-- 内容 -->
                <div class="relative z-10 flex flex-col sm:flex-row sm:items-center gap-5 p-6 sm:p-8">
                    <div class="flex-1 min-w-0">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full bg-white/15 backdrop-blur-sm border border-white/30 text-white/90 text-[11px] font-medium tracking-[0.3em] uppercase">
                            MBookTI · 直觉测验
                        </span>
                        <h2 class="mt-3 text-2xl sm:text-3xl font-bold text-white leading-snug">直觉型 MBTI 测试</h2>
                        <p class="mt-1.5 text-sm sm:text-base text-white/70">别思考，凭直觉，3 分钟找到你的类型</p>
                    </div>
                    <div class="shrink-0 self-start sm:self-auto">
                        <div class="relative inline-flex items-center gap-2 px-6 py-3 rounded-full bg-white text-indigo-600 font-bold text-sm shadow-lg shadow-indigo-900/20 overflow-hidden
                                    transition-all duration-300 group-hover:scale-105 group-hover:shadow-xl group-hover:shadow-indigo-900/30">
                            开始测试
                            <span class="transition-transform duration-300 group-hover:translate-x-0.5">→</span>
                            <span class="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-indigo-100/80 to-transparent animate-shimmer"></span>
                        </div>
                    </div>
                </div>
            </button>
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
            <button @click="reloadPage" class="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
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
