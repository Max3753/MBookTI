<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import type { TheaterScene as Scene, TheaterOption } from '../../types/mbtiTest'

const props = defineProps<{
    scene: Scene | null
}>()

const emit = defineEmits<{ choose: [option: TheaterOption] }>()

// ---- 场景主题背景映射（换场景 = 换色调） ----
const sceneThemes: Record<string, string> = {
    // 入口：老板突发通知 → 暖橙警示感
    proj_start: 'linear-gradient(135deg, #fb923c 0%, #f59e0b 45%, #ea580c 100%)',
    // J 分支：执行/判断 → 蓝紫理性感
    proj_j_branch: 'linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #8b5cf6 100%)',
    proj_j_tf: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 45%, #4f46e5 100%)',
    proj_j_end: 'linear-gradient(135deg, #4f46e5 0%, #0ea5e9 55%, #6366f1 100%)',
    // P 分支：灵感漫游 → 青绿生机感
    proj_p_branch: 'linear-gradient(135deg, #34d399 0%, #14b8a6 50%, #10b981 100%)',
    proj_p_sn: 'linear-gradient(135deg, #14b8a6 0%, #06b6d4 50%, #10b981 100%)',
    proj_p_end: 'linear-gradient(135deg, #10b981 0%, #a3e635 55%, #34d399 100%)',
}
const themeBackground = computed(() =>
    props.scene
        ? (sceneThemes[props.scene.id] ?? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%)')
        : ''
)

// ---- 对话发送者信息 ----
const senderName = computed(() => props.scene?.title ?? '')
const senderInitial = computed(() => senderName.value.charAt(0))

// ---- 打字机效果 ----
const displayedText = ref('')   // 当前已显示的字
let timer: number | undefined

// 场景变化时，重置打字机
watch(() => props.scene?.id, () => {
    displayedText.value = ''
    clearInterval(timer)
    const full = props.scene?.dialogue ?? ''
    let i = 0
    timer = window.setInterval(() => {
        i += 1
        displayedText.value = full.slice(0, i)
        if (i >= full.length) clearInterval(timer)  // 打完了停
    }, 50)  // 每 50ms 打一个字
})

onUnmounted(() => clearInterval(timer))
</script>

<template>
    <div class="relative min-h-screen flex flex-col justify-end p-4 overflow-hidden">
        <!-- 底色（过渡间隙兜底） -->
        <div class="absolute inset-0 bg-slate-900"></div>

        <!-- 场景背景：随 scene.id 交叉淡入 -->
        <Transition name="bg-fade" mode="out-in">
            <div :key="props.scene?.id ?? 'none'"
                class="absolute inset-0 animate-gradient-pan"
                :style="{ backgroundImage: themeBackground }"></div>
        </Transition>

        <!-- 氛围粒子感光斑 -->
        <div class="pointer-events-none absolute inset-0" aria-hidden="true">
            <div class="absolute -top-20 -left-20 w-64 h-64 rounded-full bg-white/15 blur-3xl animate-glow-pulse"></div>
            <div class="absolute -bottom-24 -right-16 w-72 h-72 rounded-full bg-black/15 blur-3xl animate-glow-pulse" style="animation-delay: 2s"></div>
        </div>

        <!-- 内容区 -->
        <div class="relative z-10 w-full max-w-md mx-auto flex flex-col justify-end">
            <!-- 场景角色徽章 -->
            <div class="flex justify-center mb-8">
                <div class="w-24 h-24 rounded-3xl bg-white/15 backdrop-blur-md border border-white/25
                            flex items-center justify-center text-5xl shadow-2xl shadow-black/20 animate-float">
                    {{ scene?.emoji }}
                </div>
            </div>

            <!-- 对话气泡：手机消息样式 -->
            <div class="mb-4" v-if="props.scene">
                <div class="flex items-center gap-2.5 mb-2 animate-fade-up">
                    <div class="w-9 h-9 rounded-full bg-gradient-to-br from-white/50 to-white/20 border border-white/40
                                flex items-center justify-center text-white font-bold text-sm shadow-lg">{{ senderInitial }}</div>
                    <span class="text-white/95 text-sm font-medium tracking-wide">{{ senderName }}</span>
                </div>
                <div class="relative chat-tail bg-white/95 backdrop-blur-xl rounded-3xl rounded-tl-md
                            shadow-2xl shadow-black/20 p-5 animate-fade-up"
                    :style="{ animationDelay: '0.1s' }">
                    <p class="text-gray-800 leading-relaxed min-h-[2.5rem] text-[15px]">
                        {{ displayedText }}
                        <span class="inline-block w-[2px] h-[1.1em] ml-0.5 rounded-full bg-indigo-500 align-text-bottom animate-caret"></span>
                    </p>
                </div>
            </div>

            <!-- 选项：错落淡入 -->
            <div class="space-y-2.5 pb-6">
                <button
                    v-for="(opt, i) in scene?.options ?? []"
                    :key="opt.text"
                    class="w-full text-left bg-white/95 backdrop-blur-xl hover:bg-white active:scale-[0.98] transition-all
                        rounded-2xl px-4.5 py-3.5 text-sm text-indigo-950/80 font-medium
                        shadow-xl shadow-black/15 border border-white/50
                        hover:-translate-y-0.5 hover:shadow-2xl animate-fade-up"
                    :style="{ animationDelay: (0.35 + i * 0.12) + 's' }"
                    @click="emit('choose', opt)">
                    {{ opt.text }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* 场景背景交叉淡入 */
.bg-fade-enter-from,
.bg-fade-leave-to {
    opacity: 0;
}
.bg-fade-enter-active,
.bg-fade-leave-active {
    transition: opacity 0.6s ease;
}
.bg-fade-enter-to,
.bg-fade-leave-from {
    opacity: 1;
}

/* 聊天气泡小尾巴 */
.chat-tail::before {
    content: '';
    position: absolute;
    top: -6px;
    left: 16px;
    width: 14px;
    height: 14px;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 3px;
    transform: rotate(45deg);
}
</style>
