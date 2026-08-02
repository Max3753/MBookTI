<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import type { TheaterScene as Scene, TheaterOption } from '../../types/mbtiTest'

const props = defineProps<{
    scene: Scene | null
}>()

const emit = defineEmits<{ choose: [option: TheaterOption] }>()

// ---- 场景主题背景映射（换场景 = 换纸色，报纸风格近似适配） ----
const sceneThemes: Record<string, string> = {
    // 入口：老板突发通知 → 暖纸色
    proj_start: 'linear-gradient(135deg, #FBF6EE 0%, #F7F0E6 100%)',
    // J 分支：执行/判断 → 冷纸色
    proj_j_branch: 'linear-gradient(135deg, #F2F5F8 0%, #E9EFF6 100%)',
    proj_j_tf: 'linear-gradient(135deg, #F4F2F8 0%, #ECE8F4 100%)',
    proj_j_end: 'linear-gradient(135deg, #EFF4FA 0%, #E3ECF7 100%)',
    // P 分支：灵感漫游 → 青绿纸色
    proj_p_branch: 'linear-gradient(135deg, #F2F8F4 0%, #E8F3EC 100%)',
    proj_p_sn: 'linear-gradient(135deg, #EFF7F6 0%, #E4F1EF 100%)',
    proj_p_end: 'linear-gradient(135deg, #F4F9EE 0%, #EBF3E2 100%)',
}
// 有实景图用实景图，否则回退纸色渐变
const themeBackground = computed(() => {
    if (props.scene?.image) {
        return `url("${props.scene.image}") center/cover no-repeat`
    }
    return props.scene
        ? (sceneThemes[props.scene.id] ?? 'linear-gradient(135deg, #F6F4EF 0%, #EFECE4 100%)')
        : ''
})

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
    <div class="newsprint-texture relative min-h-screen flex flex-col justify-end p-4 overflow-hidden">
        <!-- 底色（过渡间隙兜底） -->
        <div class="absolute inset-0 bg-paper dark:bg-[#17170f]"></div>

        <!-- 场景背景：随 scene.id 交叉淡入（实景图或纸色渐变兜底） -->
        <Transition name="bg-fade" mode="out-in">
            <div :key="props.scene?.id ?? 'none'"
                class="absolute inset-0"
                :style="{ backgroundImage: themeBackground }"></div>
        </Transition>

        <!-- 内容区 -->
        <div class="relative z-10 w-full max-w-md mx-auto flex flex-col justify-end">
            <!-- 场景角色徽章 -->
            <div class="flex justify-center mb-8">
                <div class="w-24 h-24 bg-paper dark:bg-[#201f16] border-2 border-ink dark:border-paper hard-shadow
                            flex items-center justify-center text-5xl animate-float">
                    {{ scene?.emoji }}
                </div>
            </div>

            <!-- 对话气泡：手机消息样式 -->
            <div class="mb-4" v-if="props.scene">
                <div class="flex items-center gap-2.5 mb-2 animate-fade-up">
                    <div class="w-9 h-9 bg-ink text-paper dark:bg-paper dark:text-ink
                                flex items-center justify-center font-serif font-bold text-sm">{{ senderInitial }}</div>
                    <span class="px-2 py-0.5 bg-paper dark:bg-[#201f16] border border-ink/40 dark:border-paper/40
                                 text-ink dark:text-paper text-sm font-medium tracking-wide">{{ senderName }}</span>
                </div>
                <div class="relative chat-tail bg-paper dark:bg-[#201f16] border-2 border-ink dark:border-paper
                            hard-shadow p-5 animate-fade-up"
                    :style="{ animationDelay: '0.1s' }">
                    <p class="text-ink dark:text-paper leading-relaxed min-h-[2.5rem] text-[15px]">
                        {{ displayedText }}
                        <span class="inline-block w-[2px] h-[1.1em] ml-0.5 bg-editorial align-text-bottom"></span>
                    </p>
                </div>
            </div>

            <!-- 选项：错落淡入 -->
            <div class="space-y-2.5 pb-6">
                <button
                    v-for="(opt, i) in scene?.options ?? []"
                    :key="opt.text"
                    class="w-full text-left bg-paper dark:bg-[#201f16] border-2 border-ink dark:border-paper
                        hover:bg-[#F0F0F0] dark:hover:bg-neutral-700 active:scale-[0.98] transition-all
                        px-4.5 py-3.5 text-sm text-ink dark:text-paper font-medium
                        hard-shadow-hover animate-fade-up"
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
    top: -8px;
    left: 16px;
    width: 14px;
    height: 14px;
    background: #F9F9F7;
    border-top: 2px solid #111111;
    border-left: 2px solid #111111;
    transform: rotate(45deg);
}
.dark .chat-tail::before {
    background: #201f16;
    border-color: #F9F9F7;
}
</style>
