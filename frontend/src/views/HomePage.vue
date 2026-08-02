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
        return new URL(`../resources/mbti_img/${code.toLowerCase()}.png`, import.meta.url).href
    } catch {
        return ''
    }
}
</script>

<template>
    <div class="newsprint-texture">
        <!-- 报头：超大衬线头条 -->
        <div class="text-center mb-10 animate-fade-up">
            <div class="edition-label text-editorial mb-4">MBookTI · 直觉版</div>
            <h1 class="np-hero text-ink dark:text-paper">{{ t.home_title }}</h1>
            <p class="mt-4 font-serif text-lg italic text-neutral-600 dark:text-neutral-300">{{ t.home_desc }}</p>
            <div class="mt-6 flex items-center justify-center gap-3 edition-label text-neutral-500 dark:text-neutral-400">
                <span>第壹号 · 2026 年 8 月 2 日</span>
                <span class="inline-block w-2 h-2 bg-editorial" aria-hidden="true"></span>
                <span>性格专刊 · PERSONALITY EDITION</span>
            </div>
            <div class="ornament-divider">❦</div>
        </div>

        <!-- 直觉型 MBTI 测试入口：报纸广告横幅（与类型列表加载无关，始终显示） -->
        <div class="max-w-3xl mx-auto mb-10 animate-fade-up">
            <button
            @click="goToTest"
            class="group relative block w-full np-card hard-shadow-hover text-left cursor-pointer select-none p-6 sm:p-8"
            aria-label="开始直觉型 MBTI 测试"
            >
                <!-- 特别报道红色顶栏 -->
                <div class="absolute top-0 left-0 right-0 h-1 bg-editorial" aria-hidden="true"></div>

                <!-- 内容 -->
                <div class="flex items-center justify-between gap-4 mb-5">
                    <span class="np-badge np-badge-editorial">特别报道 · SPECIAL REPORT</span>
                    <span class="edition-label text-neutral-500 hidden sm:inline">MBookTI · 直觉测验</span>
                </div>
                <div class="flex flex-col sm:flex-row sm:items-center gap-6">
                    <div class="flex-1 min-w-0">
                        <h2 class="text-2xl sm:text-3xl font-serif font-bold text-ink dark:text-paper leading-snug">
                            直觉型 <span class="text-editorial">MBTI</span> 测试
                        </h2>
                        <p class="mt-2 text-sm sm:text-base text-neutral-600 dark:text-neutral-300">别思考，凭直觉，3 分钟找到你的类型</p>
                    </div>
                    <div class="shrink-0 self-start sm:self-auto">
                        <span class="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper dark:bg-paper dark:text-ink font-mono text-xs font-semibold uppercase tracking-widest transition-colors duration-200 group-hover:bg-editorial">
                            开始测试
                            <span class="transition-transform duration-300 group-hover:translate-x-0.5">→</span>
                        </span>
                    </div>
                </div>
            </button>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-20 animate-fade-up">
            <div class="mx-auto max-w-md np-card px-8 py-10">
                <div class="edition-label text-editorial mb-3">排印中 · SETTING TYPE</div>
                <p class="font-serif text-2xl font-bold text-ink dark:text-paper">{{ t.loading }}<span class="animate-caret text-editorial">|</span></p>
            </div>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="loadError" class="text-center py-20 animate-fade-up">
            <div class="mx-auto max-w-md np-card px-8 py-10">
                <div class="edition-label text-editorial mb-3">发行中断 · PRESS HALT</div>
                <p class="font-serif text-2xl font-bold text-ink dark:text-paper mb-6">{{ t.load_failed }}</p>
                <button @click="reloadPage" class="np-btn np-btn-primary cursor-pointer">{{ t.retry }}</button>
            </div>
        </div>

        <!-- 数据为空 -->
        <div v-else-if="types.length === 0" class="text-center py-20 animate-fade-up">
            <div class="mx-auto max-w-md np-card px-8 py-10">
                <div class="edition-label text-editorial mb-3">本期无内容 · NO CONTENT</div>
                <p class="font-serif text-2xl font-bold text-ink dark:text-paper">{{ t.no_data }}</p>
            </div>
        </div>

        <!-- MBTI 卡片：报纸分类栏 -->
        <div v-else>
            <div class="flex items-baseline justify-between border-b-4 border-ink dark:border-paper pb-2 mb-6 animate-fade-up">
                <h2 class="font-serif text-2xl font-bold tracking-tight text-ink dark:text-paper">16 型人格全览</h2>
                <span class="edition-label text-neutral-400">ALL SIXTEEN TYPES</span>
            </div>
            <div class="border border-ink dark:border-paper animate-fade-up">
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-px bg-ink dark:bg-paper">
                    <button
                    v-for="item in types"
                    :key="item.code"
                    @click="goToType(item.code)"
                    class="group relative bg-paper dark:bg-[#201f16] p-4 text-left cursor-pointer flex items-center justify-between transition-all duration-200 hard-shadow-hover"
                    :class="user?.mbti_type_id === item.id ? 'hard-shadow' : ''"
                    >
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-1.5">
                            <div class="font-serif text-lg font-bold text-ink dark:text-paper">{{ item.code }}</div>
                            <span v-if="user?.mbti_type_id === item.id" class="np-badge np-badge-editorial leading-none">
                                我的
                            </span>
                        </div>
                        <div class="text-sm text-neutral-600 dark:text-neutral-300 mt-0.5">{{ item.name }}</div>
                        <div class="edition-label text-neutral-400 dark:text-neutral-500 mt-1 truncate">{{ item.name_en }}</div>
                    </div>
                    <div class="w-16 h-16 bg-neutral-100 dark:bg-[#2a291d] border border-ink/20 dark:border-paper/20 flex items-center justify-center overflow-hidden shrink-0 ml-3">
                        <img
                        :src="getImage(item.code)"
                        :alt="item.code"
                        class="w-full h-full object-cover"
                        :class="user?.mbti_type_id === item.id ? '' : 'newsprint-img'"
                        @error="(e: any) => e.target.style.display = 'none'"
                        >
                    </div>
                    </button>
                </div>
            </div>
        </div>

        <!-- 系统公告弹窗（必须保持在单根节点内部，否则 Transition 动画失效导致路由切换后新页面不渲染） -->
        <div v-if="currentAnnouncement" class="fixed inset-0 bg-ink/60 flex items-center justify-center z-50 p-4 animate-newsprint-in" @click.self="announcements = []">
            <div class="np-card w-full max-w-md hard-shadow">
                <div class="flex items-center justify-between px-6 py-4 border-b-2 border-ink dark:border-paper">
                    <div class="flex items-center gap-2">
                        <span class="np-badge np-badge-editorial leading-none">号外</span>
                        <span class="font-serif font-bold text-lg text-ink dark:text-paper">系统公告</span>
                        <span v-if="announcements.length > 1" class="edition-label text-neutral-400">{{ announcementIndex + 1 }}/{{ announcements.length }}</span>
                    </div>
                </div>
                <div class="px-6 py-5">
                    <h3 class="font-serif text-xl font-bold text-ink dark:text-paper mb-2">{{ currentAnnouncement.title }}</h3>
                    <p class="text-sm text-neutral-600 dark:text-neutral-300 leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">{{ currentAnnouncement.content }}</p>
                </div>
                <div class="px-6 py-4 border-t-2 border-ink dark:border-paper flex justify-end">
                    <button
                        @click="confirmAnnouncement"
                        :disabled="acking"
                        class="np-btn np-btn-primary cursor-pointer"
                    >
                        {{ acking ? '确认中...' : '我知道了' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
