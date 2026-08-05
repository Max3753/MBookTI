import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { IBookAdapter, BookFormat } from '../adapters/types'

// 阅读设置
export interface ReaderSettings {
    fontSize: number
    theme: 'light' | 'dark' | 'sepia'   // 保留兼容旧存档；实际颜色以 bgColor/fgColor 为准
    bgColor: string   // 阅读背景色（hex）
    fgColor: string   // 阅读文字色（hex）
    lineHeight: number       // 行距倍数（1.5 紧凑 / 1.8 标准 / 2.0 宽松 / 2.4 舒适）
    fontFamily: 'default' | 'serif' | 'sans'  // 阅读字体：默认 / 宋体（衬线）/ 黑体（无衬线）
    marginWidth: 'narrow' | 'standard' | 'wide'  // 页边距：窄 / 标准 / 宽
    indent: boolean          // 段落首行缩进
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
        theme: 'light',
        bgColor: '#ffffff',
        fgColor: '#1f2937',
        lineHeight: 1.9,
        fontFamily: 'default',
        marginWidth: 'standard',
        indent: true,
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
            const saved = JSON.parse(raw)
            // 旧存档可能缺新增字段，合并后补默认值（向后兼容）
            Object.assign(settings.value, {
                bgColor: '#ffffff', fgColor: '#1f2937',
                lineHeight: 1.9, fontFamily: 'default', marginWidth: 'standard', indent: true,
            }, saved)
        } catch {/* 损坏数据静默忽略 */}
    }

    /** 更新背景/文字色并持久化 */
    function setColors(bgColor: string, fgColor: string) {
        settings.value.bgColor = bgColor
        settings.value.fgColor = fgColor
        saveSettings()
    }

    return {
        adapter, format, settings,
        setAdapter, saveProgress, loadProgress, saveSettings, loadSettings, setColors
    }
})
