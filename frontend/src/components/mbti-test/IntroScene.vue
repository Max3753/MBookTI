<script setup lang="ts">
import { onMounted, onUnmounted, ref} from 'vue';

const emit = defineEmits<{ start: [] }>();
const visible = ref(false) //控制文案淡入
let timer: number | undefined

onMounted(() => {
    visible.value = true    // 进入即淡入
    timer = window.setTimeout(() => 
        emit('start'), 5000) // 5秒后开始测试
})

onUnmounted(() => clearTimeout(timer)) // 离开页面时清除定时器
</script>

<template>
    <div class="newsprint-texture relative h-full min-h-screen flex flex-col items-center justify-center cursor-pointer select-none
                overflow-hidden bg-paper dark:bg-ink"
        @click="emit('start')">

        <!-- 中央内容：错落入场 -->
        <div class="relative z-10 flex flex-col items-center px-6">
            <!-- 品牌小字 -->
            <div class="animate-fade-up" style="animation-delay: 0.1s">
                <span class="edition-label text-editorial">MBookTI · 直觉测验</span>
            </div>

            <!-- 主文案 -->
            <h1 class="mt-8 text-4xl font-serif font-black text-ink dark:text-paper text-center leading-snug animate-fade-up"
                style="animation-delay: 0.3s">
                别思考，凭直觉<br />选择吸引你的画面
            </h1>

            <!-- 点击开始提示 -->
            <div class="mt-12 flex flex-col items-center animate-fade-up" style="animation-delay: 0.6s">
                <div
                    class="relative px-8 py-3 bg-ink text-paper dark:bg-paper dark:text-ink border-2 border-ink dark:border-paper
                           font-mono text-xs font-semibold uppercase tracking-[0.25em] transition-all duration-700"
                    :class="visible ? 'hard-shadow' : 'opacity-60'">
                    点击任意处开始
                </div>
                <p class="mt-3 text-center text-neutral-500 dark:text-neutral-400 text-xs tracking-wider">全程约 3 分钟</p>
            </div>
        </div>
    </div>
</template>
