<script setup lang="ts">
import { ref } from 'vue'
import { useReaderStore } from '../stores/reader'
import { createAdapter } from '../adapters'


const store = useReaderStore()
const fileInput = ref<HTMLInputElement | null>(null)
const container = ref<HTMLElement | null>(null)
const error = ref('')
const bookTitle = ref('')
const total = ref(0)

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
    } catch (e: any) {
        error.value = e.message || '打开失败'
        store.setAdapter(null, '')
    } finally {
        input.value = ''                           // 重置 input，允许重复选同一文件
    }
}

async function next() {
    try { await store.adapter?.next() } catch (e: any) { error.value = e.message || '翻页失败' }
    store.saveProgress()
}
async function prev() {
    try { await store.adapter?.prev() } catch (e: any) { error.value = e.message || '翻页失败' }
    store.saveProgress()
}
</script>

<template>
    <div class="max-w-3xl mx-auto px-4 py-8">
        <input ref="fileInput" type="file" accept=".txt,.epub" class="hidden" @change="onFilePicked" />
        <button class="np-btn np-btn-ghost" @click="openPicker">选择 电子书 文件</button>

        <p v-if="error" class="text-red-500 mt-2">{{ error }}</p>
        <h1 v-if="bookTitle" class="font-serif font-black text-2xl mt-6">{{ bookTitle }}</h1>

        <div ref="container" class="mt-4 h-[70vh] border border-ink/10"></div>

        <div v-if="store.adapter" class="mt-6 flex gap-4">
            <button class="np-btn np-btn-ghost" @click="prev">上一段</button>
            <button class="np-btn" @click="next">下一段</button>
        </div>
    </div>
</template>