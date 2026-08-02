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
    <div class="newsprint-texture min-h-screen flex flex-col items-center px-4 py-6
                bg-paper dark:bg-ink">
        <div class="w-full max-w-md flex flex-col flex-1">

            <!-- 进度条：渐变 + 流光 -->
            <div class="flex items-center gap-3">
                <div class="flex-1 h-3 bg-divider dark:bg-neutral-700 border border-ink dark:border-paper overflow-hidden">
                    <div class="relative h-full bg-ink dark:bg-paper transition-all duration-500 ease-out"
                        :style="{ width: (index / total * 100) + '%' }"></div>
                </div>
                <span class="text-sm font-semibold text-ink dark:text-paper font-mono shrink-0 tabular-nums">
                    <span :key="index" class="inline-block animate-scale-in">{{ index + 1 }}</span>
                    <span class="text-gray-400 font-normal"> / {{ total }}</span>
                </span>
            </div>

            <!-- 题目切换：旧题淡出 + 新题滑入 -->
            <Transition name="question" mode="out-in">
                <div :key="question.id" class="flex flex-col flex-1">
                    <h2 class="text-center text-ink dark:text-paper font-serif font-bold text-lg mt-8 mb-5 animate-fade-up">凭直觉选一个</h2>

                    <div class="flex-1 grid grid-cols-2 gap-3">
                        <!-- 左选项 -->
                        <button
                            class="group relative overflow-hidden bg-paper dark:bg-[#201f16] border-2 border-ink dark:border-paper
                                   hard-shadow-hover
                                   transition-all duration-200 active:scale-95 animate-fade-up"
                            :style="{ animationDelay: '0.15s' }"
                            @click="emit('answer', 'left')">
                            <div class="relative text-6xl py-14 flex items-center justify-center
                                        bg-neutral-100 dark:bg-neutral-800
                                        transition-transform duration-300 group-hover:scale-110">
                                {{ question.left.emoji }}
                            </div>
                            <div class="py-3.5 text-center text-sm font-medium text-ink dark:text-paper">{{ question.left.label }}</div>
                        </button>

                        <!-- 右选项 -->
                        <button
                            class="group relative overflow-hidden bg-paper dark:bg-[#201f16] border-2 border-ink dark:border-paper
                                   hard-shadow-hover
                                   transition-all duration-200 active:scale-95 animate-fade-up"
                            :style="{ animationDelay: '0.3s' }"
                            @click="emit('answer', 'right')">
                            <div class="relative text-6xl py-14 flex items-center justify-center
                                        bg-neutral-100 dark:bg-neutral-800
                                        transition-transform duration-300 group-hover:scale-110">
                                {{ question.right.emoji }}
                            </div>
                            <div class="py-3.5 text-center text-sm font-medium text-ink dark:text-paper">{{ question.right.label }}</div>
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
