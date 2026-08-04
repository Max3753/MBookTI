<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
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

const { isFullscreen, isSupported: fullscreenSupported, toggle: toggleFullscreen } = useReaderFullscreen(readerRoot)

// 全屏进出会改变容器可视高度 → TXT 分页失效，重排并保持当前进度
watch(isFullscreen, () => {
    nextTick(() => requestAnimationFrame(() => {
        void store.adapter?.relayout?.()
    }))
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
        <button class="np-btn np-btn-ghost" @click="openPicker">选择 电子书 文件</button>

        <p v-if="error" class="text-red-500 mt-2">{{ error }}</p>

        <div ref="readerRoot" class="reader-root mt-4">
            <h1 v-if="bookTitle" class="font-serif font-black text-2xl mb-4">{{ bookTitle }}</h1>

            <div ref="container" class="reader-container h-[70vh] border border-ink/10 overflow-hidden"></div>

            <div v-if="store.adapter" class="mt-6 flex gap-4 items-center">
                <button class="np-btn np-btn-ghost" @click="prev">上一页</button>
                <button class="np-btn" @click="next">下一页</button>
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

/* 全屏时：外层占满视口，阅读容器吃掉剩余高度（标题/按钮保留自然高度） */
.reader-root:fullscreen {
    width: 100vw;
    height: 100vh;
    background: #fff;
    padding: 1rem;
}
.reader-root:fullscreen .reader-container {
    flex: 1;
    height: auto;
    min-height: 0;
}
</style>