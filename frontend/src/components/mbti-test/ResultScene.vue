<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { AxiosError } from 'axios'
import { getMbtiTypes, updateMyProfile } from '../../api'
import { useAuth } from '../../composables/useAuth'
import type { TypeFeedback } from '../../types/mbtiTest'

const props = defineProps<{
    type: string
    detail: Record<'EI' | 'SN' | 'TF' | 'JP', number>   // 每对里前者的百分比
    feedback: Omit<TypeFeedback, 'type'> | null
}>()

// ---- 保存结果到个人资料（登录态） ----
const router = useRouter()
const { user, isLoggedIn, updateUser } = useAuth()

// 保存状态
const saving = ref(false)
const saved = ref(false)
const saveMsg = ref('')
const saveOk = ref(false)
const mbtiTypes = ref<{ id: number; code: string }[]>([])

const saveButtonText = computed(() => (saving.value ? '保存中...' : saved.value ? '已保存 ✓' : '保存到我的资料'))
const saveButtonDisabled = computed(() => saving.value || saved.value)

// 拉取 16 型列表（缓存，避免重复请求）
async function loadMbtiTypes() {
    if (mbtiTypes.value.length > 0) return
    try {
        const res = await getMbtiTypes()
        mbtiTypes.value = res.data || []
    } catch {
        mbtiTypes.value = []
    }
}

// 保存链路：code → getMbtiTypes 找 id → updateMyProfile → 同步登录态
async function saveResult() {
    if (saving.value || saved.value || !isLoggedIn.value) return
    saving.value = true
    saveMsg.value = ''
    try {
        await loadMbtiTypes()
        const found = mbtiTypes.value.find(t => t.code === props.type)
        if (!found) {
            saveOk.value = false
            saveMsg.value = '未找到对应的 MBTI 类型，请稍后再试'
            return
        }
        await updateMyProfile({ mbti_type_id: found.id })
        updateUser({ mbti_type_id: found.id })
        saved.value = true
        saveOk.value = true
        saveMsg.value = '已保存到你的资料'
    } catch (err) {
        saveOk.value = false
        const detail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail
        saveMsg.value = detail || '保存失败，请稍后再试'
    } finally {
        saving.value = false
    }
}

// 进入结果页时预判：当前用户资料已是该类型则直接显示已保存
onMounted(() => {
    if (isLoggedIn.value) {
        loadMbtiTypes().then(() => {
            const found = mbtiTypes.value.find(t => t.code === props.type)
            if (found && user.value?.mbti_type_id === found.id) {
                saved.value = true
            }
        })
    }
})

// 角色图 URL（复用 HomePage 的模式）
function getImage(code: string): string {
    try {
        return new URL(`../../resources/${code.toLowerCase()}.png`, import.meta.url).href
    } catch {
        return ''
    }
}

// 维度对的展示信息：key 是一对，value 是显示文本
const dimensions = [
    { pair: 'EI', label: '精力来源' },
    { pair: 'SN', label: '认知方式' },
    { pair: 'TF', label: '决策依据' },
    { pair: 'JP', label: '生活态度' },
] as const

// 维度对比色：左（前者）暖色 vs 右（后者）冷色
const dimensionVisuals = {
    EI: {
        left: 'bg-gradient-to-r from-orange-400 to-amber-400', leftText: 'text-orange-500',
        right: 'bg-gradient-to-r from-sky-400 to-blue-500', rightText: 'text-sky-500',
    },
    SN: {
        left: 'bg-gradient-to-r from-amber-400 to-yellow-400', leftText: 'text-amber-500',
        right: 'bg-gradient-to-r from-cyan-400 to-blue-500', rightText: 'text-cyan-500',
    },
    TF: {
        left: 'bg-gradient-to-r from-rose-400 to-red-400', leftText: 'text-rose-500',
        right: 'bg-gradient-to-r from-emerald-400 to-green-500', rightText: 'text-emerald-500',
    },
    JP: {
        left: 'bg-gradient-to-r from-orange-400 to-amber-500', leftText: 'text-orange-500',
        right: 'bg-gradient-to-r from-teal-400 to-cyan-500', rightText: 'text-teal-500',
    },
} as const
</script>

<template>
    <div class="relative min-h-screen px-4 py-10 overflow-hidden
                bg-gradient-to-b from-indigo-50 via-violet-50/60 to-fuchsia-50">
        <!-- 顶部光晕 -->
        <div class="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[140%] h-96
                    bg-[radial-gradient(ellipse_at_top,rgba(129,140,248,0.28),transparent_70%)]" aria-hidden="true"></div>

        <div class="relative max-w-md mx-auto">
            <!-- 类型揭晓：放大浮现 -->
            <div class="text-center animate-scale-in">
                <p class="text-xs tracking-[0.4em] text-indigo-400 font-semibold">你的 MBTI 类型</p>
                <h1 class="mt-3 text-5xl font-extrabold tracking-wide
                           bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent
                        drop-shadow-sm">{{ props.type }}</h1>
            </div>
            <p class="text-center text-gray-500 mt-3 animate-fade-up" style="animation-delay: 0.15s">{{ feedback?.metaphor }}</p>

            <!-- 角色图：延迟浮入 + 玻璃框 -->
            <div class="flex justify-center my-8 animate-scale-in" style="animation-delay: 0.3s">
                <div v-if="getImage(props.type)"
                    class="p-2.5 rounded-[2rem] bg-white/70 backdrop-blur-xl shadow-xl shadow-indigo-500/15">
                    <img :src="getImage(props.type)"
                        :alt="props.type"
                        class="w-36 h-36 rounded-[1.5rem] object-cover animate-float" />
                </div>
            </div>

            <!-- 维度条：依次展开 + 左暖右冷 -->
            <div class="space-y-4">
                <div v-for="(d, i) in dimensions" :key="d.pair"
                    class="bg-white/70 backdrop-blur-xl rounded-3xl p-5 shadow-xl shadow-indigo-500/10 animate-fade-up"
                    :style="{ animationDelay: (0.45 + i * 0.12) + 's' }">
                    <div class="flex justify-between items-center text-sm mb-3">
                        <span class="flex items-baseline gap-2">
                            <span class="font-extrabold text-lg" :class="dimensionVisuals[d.pair].leftText">{{ d.pair[0] }}</span>
                            <span class="text-gray-600 font-medium">{{ d.label }}</span>
                        </span>
                        <span class="font-extrabold text-lg" :class="dimensionVisuals[d.pair].rightText">{{ d.pair[1] }}</span>
                    </div>
                    <div class="flex h-3 bg-gray-100/80 rounded-full overflow-hidden">
                        <div class="h-full rounded-full bar-fill"
                            :class="dimensionVisuals[d.pair].left"
                            :style="{ width: detail[d.pair] + '%', animationDelay: (0.55 + i * 0.12) + 's' }"></div>
                        <div class="h-full rounded-full bar-fill"
                            :class="dimensionVisuals[d.pair].right"
                            :style="{ width: (100 - detail[d.pair]) + '%', animationDelay: (0.7 + i * 0.12) + 's' }"></div>
                    </div>
                    <div class="flex justify-between text-xs mt-2">
                        <span class="font-semibold" :class="dimensionVisuals[d.pair].leftText">{{ detail[d.pair] }}%</span>
                        <span class="font-semibold" :class="dimensionVisuals[d.pair].rightText">{{ 100 - detail[d.pair] }}%</span>
                    </div>
                </div>
            </div>

            <!-- 三个一反馈：错落浮现 -->
            <div class="mt-6 space-y-3">
                <div class="bg-white/70 backdrop-blur-xl rounded-3xl p-5 shadow-xl shadow-indigo-500/10 animate-fade-up"
                    style="animation-delay: 1.05s">
                    <div class="text-xs font-bold text-indigo-500 mb-1.5 tracking-widest">你的盲区</div>
                    <p class="text-sm text-gray-700 leading-relaxed">{{ feedback?.blindSpot }}</p>
                </div>
                <div class="bg-white/70 backdrop-blur-xl rounded-3xl p-5 shadow-xl shadow-indigo-500/10 animate-fade-up"
                    style="animation-delay: 1.2s">
                    <div class="text-xs font-bold text-indigo-500 mb-1.5 tracking-widest">相处指南</div>
                    <p class="text-sm text-gray-700 leading-relaxed">{{ feedback?.manual }}</p>
                </div>
            </div>

            <!-- 保存结果：登录可保存到资料 / 未登录引导 -->
            <div class="mt-6 animate-fade-up" style="animation-delay: 1.35s">
                <div class="bg-white/70 backdrop-blur-xl rounded-3xl p-5 shadow-xl shadow-indigo-500/10">
                    <div class="text-xs font-bold text-indigo-500 mb-1.5 tracking-widest">保存结果</div>
                    <template v-if="isLoggedIn">
                        <p class="text-sm text-gray-600 mb-3 leading-relaxed">
                            把 <span class="font-bold text-gray-800">{{ props.type }}</span> 保存到你的个人资料，
                            AI 推荐与首页「我的」标记将基于此类型。
                        </p>
                        <button
                            :disabled="saveButtonDisabled"
                            @click="saveResult"
                            class="w-full py-3 rounded-2xl font-semibold text-white transition
                                   bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500
                                   shadow-lg shadow-indigo-500/25
                                   disabled:opacity-60 disabled:cursor-not-allowed">
                            {{ saveButtonText }}
                        </button>
                        <p v-if="saveMsg" class="text-xs mt-3 font-medium"
                            :class="saveOk ? 'text-emerald-500' : 'text-red-500'">{{ saveMsg }}</p>
                    </template>
                    <template v-else>
                        <p class="text-sm text-gray-600 mb-3 leading-relaxed">
                            登录后即可把 <span class="font-bold text-gray-800">{{ props.type }}</span> 保存到个人资料，
                            获得更精准的 AI 推荐。
                        </p>
                        <button
                            @click="router.push('/login')"
                            class="w-full py-3 rounded-2xl font-semibold text-white transition
                                   bg-indigo-600 hover:bg-indigo-700
                                   shadow-lg shadow-indigo-500/25">
                            去登录
                        </button>
                    </template>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* 维度条展开动画 */
@keyframes bar-expand {
    from { transform: scaleX(0); }
    to { transform: scaleX(1); }
}
.bar-fill {
    transform-origin: left center;
    animation: bar-expand 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
}
</style>
