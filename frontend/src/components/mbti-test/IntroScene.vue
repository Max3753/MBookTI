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
    <div class="relative h-full min-h-screen flex flex-col items-center justify-center cursor-pointer select-none
                overflow-hidden bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 animate-gradient-pan"
        @click="emit('start')">

        <!-- 四角光晕：呼吸式辉光 -->
        <div class="pointer-events-none absolute inset-0" aria-hidden="true">
            <div class="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-fuchsia-300/40 blur-3xl animate-glow-pulse"></div>
            <div class="absolute -bottom-28 -right-20 w-80 h-80 rounded-full bg-indigo-300/40 blur-3xl animate-glow-pulse" style="animation-delay: 1.5s"></div>
            <div class="absolute top-1/3 -right-24 w-56 h-56 rounded-full bg-violet-300/30 blur-3xl animate-glow-pulse" style="animation-delay: 3s"></div>
            <div class="absolute bottom-1/4 -left-16 w-48 h-48 rounded-full bg-sky-300/25 blur-3xl animate-glow-pulse" style="animation-delay: 4.5s"></div>
        </div>

        <!-- 中央内容：错落入场 -->
        <div class="relative z-10 flex flex-col items-center px-6">
            <!-- 品牌小字 -->
            <div class="animate-fade-up" style="animation-delay: 0.1s">
                <span class="text-white/60 text-xs tracking-[0.45em] uppercase">MBookTI · 直觉测验</span>
            </div>

            <!-- 主文案 -->
            <h1 class="mt-8 text-4xl font-bold text-white text-center leading-snug animate-fade-up"
                style="animation-delay: 0.3s">
                别思考，凭直觉<br />选择吸引你的画面
            </h1>

            <!-- 点击开始提示 -->
            <div class="mt-12 flex flex-col items-center animate-fade-up" style="animation-delay: 0.6s">
                <div
                    class="relative px-7 py-3 rounded-full bg-white/15 backdrop-blur-md border border-white/30
                           text-white text-sm tracking-[0.25em] overflow-hidden transition-all duration-700"
                    :class="visible ? 'border-white/60 shadow-2xl shadow-fuchsia-400/40' : 'border-white/30'">
                    点击任意处开始
                    <span class="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></span>
                </div>
                <p class="mt-3 text-center text-white/60 text-xs tracking-wider">全程约 3 分钟</p>
            </div>
        </div>
    </div>
</template>
