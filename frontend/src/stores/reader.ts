import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { IBookAdapter, BookFormat } from '../adapters/types'

// 阅读设置
export interface ReaderSettings {
    fontSize: number
    theme: 'light' | 'dark' | 'sepia'
}

export const useReaderStore = defineStore('reader', () => {
    // --当前打开的书--
    const adapter = ref<IBookAdapter | null>(null)
    const format = ref<BookFormat | null>(null)

    // 进度存储键（由文件 hash 生成，外部传入）
    let progressKey = ''

    // --阅读设置（独立持久化，与进度分开）--
    const settings = ref<ReaderSettings>({
        fontSize: 16,
        theme: 'light'
    })

    /** 唯一入口：换书。销毁旧书 → 换新 → 自动恢复进度 */
    function setAdapter(instance: IBookAdapter | null, fileKey: string) {
        adapter.value?.destroy()    // 销毁旧书
        adapter.value = instance
        format.value = instance?.format ?? null
        progressKey = fileKey
        if (instance) loadProgress()
    }

    function saveProgress() {
        if (!adapter.value || !progressKey) return
        const pos = adapter.value.getProgress()
        localStorage.setItem(`reader_progress_${progressKey}`, JSON.stringify(pos))
    }

    function loadProgress() {
        if (!adapter.value || !progressKey) return
        const raw = localStorage.getItem(`reader_progress_${progressKey}`)
        if (!raw) return
        try {
            adapter.value.setProgress(JSON.parse(raw))
        } catch {/* 损坏数据静默忽略 */}
    }

    function saveSettings() {
        localStorage.setItem('reader_settings', JSON.stringify(settings.value))
    }

    function loadSettings() {
        const raw = localStorage.getItem('reader_settings')
        if (!raw) return
        try {
            Object.assign(settings.value, JSON.parse(raw))
        } catch {/* 损坏数据静默忽略 */}
    }

    return {
        adapter, format, settings,
        setAdapter, saveProgress, loadProgress, saveSettings, loadSettings
    }
})
