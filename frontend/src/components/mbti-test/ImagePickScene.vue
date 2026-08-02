<script setup lang="ts">
import type { ImageQuestion } from '../../types/mbtiTest';

// props: 从父组件（主页面）传入的只读数据
const props = defineProps<{
    question: ImageQuestion
    index: number
    total: number
}> ()

// emit: 向父组件发送事件
const emit = defineEmits<{
    answer: [side: 'left' | 'right']
}>()
</script>

<template>
    <div class="min-h-screen flex flex-col items-center px-4 py-6
                bg-gradient-to-b from-indigo-50 via-violet-50 to-fuchsia-50">
        <div class="w-full max-w-md flex flex-col flex-1">

            <!-- 进度条：渐变 + 流光 -->
            <div class="flex items-center gap-3">
                <div class="flex-1 h-2.5 bg-white/80 backdrop-blur rounded-full overflow-hidden shadow-inner shadow-indigo-100">
                    <div class="relative h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500
                                transition-all duration-500 ease-out overflow-hidden"
                        :style="{ width: (index / total * 100) + '%' }">
                        <span class="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-shimmer"></span>
                    </div>
                </div>
                <span class="text-sm font-semibold text-indigo-500/90 shrink-0 tabular-nums">
                    <span :key="index" class="inline-block animate-scale-in">{{ index + 1 }}</span>
                    <span class="text-gray-400 font-normal"> / {{ total }}</span>
                </span>
            </div>

            <!-- 题目切换：旧题淡出 + 新题滑入 -->
            <Transition name="question" mode="out-in">
                <div :key="question.id" class="flex flex-col flex-1">
                    <h2 class="text-center text-indigo-900/70 text-lg mt-8 mb-5 animate-fade-up">凭直觉选一个</h2>

                    <div class="flex-1 grid grid-cols-2 gap-3">
                        <!-- 左选项 -->
                        <button
                            class="group relative rounded-3xl overflow-hidden bg-white/70 backdrop-blur-xl
                                   shadow-xl shadow-indigo-500/10
                                   transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl hover:shadow-indigo-500/20
                                   active:scale-95 animate-fade-up"
                            :style="{ animationDelay: '0.15s' }"
                            @click="emit('answer', 'left')">
                            <!-- 按下光晕反馈 -->
                            <span class="pointer-events-none absolute inset-0 z-10 rounded-3xl
                                         bg-[radial-gradient(circle_at_center,rgba(129,140,248,0.4),transparent_70%)]
                                         opacity-0 scale-90 transition-all duration-200
                                         group-active:opacity-100 group-active:scale-100"></span>
                            <div class="relative text-6xl py-14 flex items-center justify-center
                                        bg-gradient-to-br from-indigo-100/90 to-violet-200/70
                                        transition-transform duration-300 group-hover:scale-110">
                                {{ question.left.emoji }}
                            </div>
                            <div class="py-3.5 text-center text-sm font-medium text-indigo-950/70">{{ question.left.label }}</div>
                        </button>

                        <!-- 右选项 -->
                        <button
                            class="group relative rounded-3xl overflow-hidden bg-white/70 backdrop-blur-xl
                                   shadow-xl shadow-fuchsia-500/10
                                   transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl hover:shadow-fuchsia-500/20
                                   active:scale-95 animate-fade-up"
                            :style="{ animationDelay: '0.3s' }"
                            @click="emit('answer', 'right')">
                            <span class="pointer-events-none absolute inset-0 z-10 rounded-3xl
                                         bg-[radial-gradient(circle_at_center,rgba(217,70,239,0.4),transparent_70%)]
                                         opacity-0 scale-90 transition-all duration-200
                                         group-active:opacity-100 group-active:scale-100"></span>
                            <div class="relative text-6xl py-14 flex items-center justify-center
                                        bg-gradient-to-br from-fuchsia-100/90 to-violet-200/70
                                        transition-transform duration-300 group-hover:scale-110">
                                {{ question.right.emoji }}
                            </div>
                            <div class="py-3.5 text-center text-sm font-medium text-indigo-950/70">{{ question.right.label }}</div>
                        </button>
                    </div>
                </div>
            </Transition>
        </div>
    </div>
</template>

<style scoped>
/* 题目切换过渡：旧题向左淡出，新题从右滑入 */
.question-enter-from {
    opacity: 0;
    transform: translateX(48px);
}
.question-enter-active {
    transition: all 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}
.question-enter-to {
    opacity: 1;
    transform: translateX(0);
}
.question-leave-from {
    opacity: 1;
    transform: translateX(0);
}
.question-leave-active {
    transition: all 0.35s ease;
}
.question-leave-to {
    opacity: 0;
    transform: translateX(-48px);
}
</style>
