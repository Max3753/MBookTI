<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useReaderStore } from '../stores/reader'
import { createAdapter } from '../adapters'
import { useReaderFullscreen } from '../composables/useReaderFullscreen'


const store = useReaderStore()
const fileInput = ref<HTMLInputElement | null>(null)
const container = ref<HTMLElement | null>(null)
// 全屏目标：容器 + 操作条的外层，全屏后仍能翻页/退出
const readerRoot = ref<HTMLElement | null>(null)
const error = ref('')
const bookTitle = ref('')
const total = ref(0)
const showColors = ref(false)

const { isFullscreen, isSupported: fullscreenSupported, toggle: toggleFullscreen } = useReaderFullscreen(readerRoot)

// 预设背景色板（背景 + 配套文字色）
const PRESET_COLORS: { name: string; bg: string; fg: string }[] = [
    { name: '明亮', bg: '#ffffff', fg: '#1f2937' },
    { name: '米黄', bg: '#f5ecd7', fg: '#5b4636' },
    { name: '浅绿', bg: '#cfe8cf', fg: '#2d4a22' },
    { name: '夜间', bg: '#1a1a1a', fg: '#c9c9c9' },
]

// 感知亮度决定文字色（自定义背景时自动选深/浅字）
function contrastText(hex: string): string {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? '#1f2937' : '#f3f4f6'
}

function applyColors(bg: string, fg: string) {
    store.setColors(bg, fg)
    showColors.value = false
}

function onCustomColor(event: Event) {
    const input = event.target as HTMLInputElement
    if (!input.value) return
    store.setColors(input.value, contrastText(input.value))
}

// 全屏进出会改变容器可视高度 → TXT 分页失效，重排并保持当前进度
watch(isFullscreen, () => {
    nextTick(() => requestAnimationFrame(() => {
        void store.adapter?.relayout?.()
    }))
})

// 背景/文字色变更 → 应用到当前书
watch(() => [store.settings.bgColor, store.settings.fgColor] as const, ([bg, fg]) => {
    void store.adapter?.setTheme?.(bg, fg)
})

onMounted(() => {
    store.loadSettings()   // 恢复持久化的阅读设置
})

function openPicker() { fileInput.value?.click() }

async function onFilePicked(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    error.value = ''
    try {
        const adapter = createAdapter(file)
        await adapter.load()                       // 先 load：metadata 才有值
        bookTitle.value = adapter.metadata.title   // 书名现在能显示了
        total.value = adapter.getTotal()
        store.setAdapter(adapter, `${file.name}_${file.size}`)  // 再设 store
        if (container.value) await adapter.renderTo(container.value)
        await adapter.setTheme?.(store.settings.bgColor, store.settings.fgColor)  // 应用当前背景色
        store.saveProgress()
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : '打开失败'
        store.setAdapter(null, '')
    } finally {
        input.value = ''                           // 重置 input，允许重复选同一文件
    }
}

async function next() {
    try { await store.adapter?.next() } catch (e: unknown) { error.value = e instanceof Error ? e.message : '翻页失败' }
    store.saveProgress()
}
async function prev() {
    try { await store.adapter?.prev() } catch (e: unknown) { error.value = e instanceof Error ? e.message : '翻页失败' }
    store.saveProgress()
}
</script>

<template>
    <div class="max-w-3xl mx-auto px-4 py-8">
        <input ref="fileInput" type="file" accept=".txt,.epub" class="hidden" @change="onFilePicked" />
        <div>
            <button class="np-btn np-btn-primary" @click="openPicker">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                选择电子书文件
            </button>
            <p class="text-xs text-gray-500 mt-2">支持 EPUB / TXT 格式 · 阅读进度自动保存</p>
        </div>

        <p v-if="error" class="text-red-500 mt-2">{{ error }}</p>

        <div ref="readerRoot" class="reader-root mt-4" :style="{ '--reader-bg': store.settings.bgColor }">
            <h1 v-if="bookTitle" class="font-serif font-black text-2xl mb-4">{{ bookTitle }}</h1>

            <div ref="container" class="reader-container h-[70vh] border border-ink/10 overflow-hidden"></div>

            <div v-if="store.adapter" class="mt-6 flex gap-4 items-center">
                <button class="np-btn np-btn-ghost" @click="prev">上一页</button>
                <button class="np-btn" @click="next">下一页</button>

                <div class="relative">
                    <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="showColors = !showColors">背景色</button>
                    <div v-if="showColors" class="absolute right-0 top-full mt-2 z-10 w-56 bg-white border border-ink/10 shadow-lg p-3">
                        <div class="flex gap-2 flex-wrap">
                            <button
                                v-for="c in PRESET_COLORS"
                                :key="c.bg"
                                class="w-8 h-8 rounded-full border border-ink/20 cursor-pointer"
                                :style="{ backgroundColor: c.bg }"
                                :title="c.name"
                                @click="applyColors(c.bg, c.fg)"
                            ></button>
                        </div>
                        <div class="mt-3 flex items-center gap-2">
                            <input type="color" class="w-8 h-8 p-0 border-0 cursor-pointer" :value="store.settings.bgColor" @input="onCustomColor" />
                            <span class="text-xs text-gray-500">自定义背景色</span>
                        </div>
                    </div>
                </div>

                <button
                    v-if="fullscreenSupported"
                    class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs ml-auto"
                    @click="toggleFullscreen"
                >
                    {{ isFullscreen ? '退出全屏' : '全屏' }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.reader-root {
    display: flex;
    flex-direction: column;
}

/* 全屏时：外层占满视口，阅读容器吃掉剩余高度（标题/按钮保留自然高度）
   背景跟随用户设置的自定义背景色 */
.reader-root:fullscreen {
    width: 100vw;
    height: 100vh;
    background: var(--reader-bg, #fff);
    padding: 1rem;
}
.reader-root:fullscreen .reader-container {
    flex: 1;
    height: auto;
    min-height: 0;
}
</style>