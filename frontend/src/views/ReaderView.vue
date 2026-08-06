<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useReaderStore } from '../stores/reader'
import { createAdapter } from '../adapters'
import { useReaderFullscreen } from '../composables/useReaderFullscreen'
import { useAuth } from '../composables/useAuth'
import {
    saveReaderProgress,
    getReaderProgress,
    getReadingHistory,
    deleteReadingRecord,
    type ReadingRecordItem,
} from '../api/reader'
import {
    hashFile,
    isFileSystemAccessSupported,
    pickLocalBooks,
    saveFileHandle,
    getFileHandle,
    deleteFileHandle,
    getFileFromHandle,
} from '../utils/readerLocal'
import type { ToCItem } from '../adapters/types'


const store = useReaderStore()
const { isLoggedIn } = useAuth()
const fileInput = ref<HTMLInputElement | null>(null)
const container = ref<HTMLElement | null>(null)
// 全屏目标：容器 + 操作条的外层，全屏后仍能翻页/退出
const readerRoot = ref<HTMLElement | null>(null)
const error = ref('')
const bookTitle = ref('')
const bookAuthor = ref('')
const showColors = ref(false)

// ---- 阅读历史（云端进度记录，仅登录用户）----
const history = ref<ReadingRecordItem[]>([])
const historyLoading = ref(false)
const historyTotal = ref(0)
// 当前打开书的内容哈希（book_key），进度云端同步的依据；空串 = 本地书
const currentBookKey = ref('')

// 目录抽屉
const tocOpen = ref(false)
const tocItems = ref<ToCItem[]>([])

// PDF 缩放（仅 PDF 显示控件；100 = 适配容器宽度）
const ZOOM_MIN = 50
const ZOOM_MAX = 200
const ZOOM_STEP = 25
const zoom = ref(100)
const isPdf = computed(() => store.adapter?.format === 'pdf')

function applyZoom() { void store.adapter?.setZoom?.(zoom.value) }
function zoomIn() { zoom.value = Math.min(ZOOM_MAX, zoom.value + ZOOM_STEP); applyZoom() }
function zoomOut() { zoom.value = Math.max(ZOOM_MIN, zoom.value - ZOOM_STEP); applyZoom() }
function resetZoom() { zoom.value = 100; applyZoom() }

// ---- 排版设置（字体 / 行距 / 页边距 / 首行缩进）----
const showTypo = ref(false)
const FONT_OPTIONS = [
    { value: 'default', label: '默认' },
    { value: 'serif', label: '宋体' },
    { value: 'sans', label: '黑体' },
] as const
const LINE_OPTIONS = [
    { value: 1.5, label: '紧凑' },
    { value: 1.8, label: '标准' },
    { value: 2.0, label: '宽松' },
    { value: 2.4, label: '舒适' },
] as const
const MARGIN_OPTIONS = [
    { value: 'narrow', label: '窄' },
    { value: 'standard', label: '标准' },
    { value: 'wide', label: '宽' },
] as const

// 字体栈 → CSS 变量（TXT 段落渲染在阅读器容器内，靠 .reader-container 规则生效）
function fontFamilyCss(f: string): string {
    if (f === 'serif') return "'Songti SC', 'SimSun', 'Noto Serif CJK SC', Georgia, 'Times New Roman', serif"
    if (f === 'sans') return "'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Helvetica Neue', Arial, sans-serif"
    return ''
}

// 页边距 → 容器 padding（EPUB iframe 被压缩出留白；TXT 段落区收缩；PDF canvas 相应变窄）
function marginPaddingCss(m: string): string {
    if (m === 'narrow') return '0.5rem 1rem'
    if (m === 'wide') return '2.5rem 3.5rem'
    return '1.25rem 2rem'
}

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
        refreshProgress()
    }))
})

// 背景/文字色 + 字号 + 排版参数变更 → 应用到当前书（任意设置途径统一走此 watch 持久化+重排）
watch(
    () => [
        store.settings.fontSize,
        store.settings.bgColor,
        store.settings.fgColor,
        store.settings.lineHeight,
        store.settings.fontFamily,
        store.settings.marginWidth,
        store.settings.indent,
    ] as const,
    () => {
        store.saveSettings()
        void store.adapter?.setTheme?.(store.settings.bgColor, store.settings.fgColor, {
            lineHeight: store.settings.lineHeight,
            fontFamily: store.settings.fontFamily,
            marginWidth: store.settings.marginWidth,
            indent: store.settings.indent,
        })
        // 行距/边距/字体影响 TXT 分页高度 → 等 DOM 应用新样式后重排，保持当前段落锚点
        nextTick(() => {
            void store.adapter?.relayout?.()
            refreshProgress()
        })
    }
)

onMounted(() => {
    store.loadSettings()   // 恢复持久化的阅读设置
    if (isLoggedIn.value) void loadHistory()
    window.addEventListener('keydown', onKeydown)
})

// 离开阅读器时清理内存态：store.adapter 是全局单例，若不清理，
// 从个人主页等页面 SPA 跳回 /reader 时会直接渲染阅读台（且容器空白，
// 因为 onMounted 不再重新 renderTo），而不是空态主页；刷新后才会正常。
// 进度已持久化（localStorage + 云端），下次选同一文件会自动续读，不影响。
onUnmounted(() => {
    window.removeEventListener('keydown', onKeydown)
    if (progressSaveTimer !== null) {
        window.clearTimeout(progressSaveTimer)
        progressSaveTimer = null
    }
    store.setAdapter(null, '')
    currentBookKey.value = ''
})

// ---- 阅读历史 ----
async function loadHistory() {
    historyLoading.value = true
    try {
        const res = await getReadingHistory(1, 50)
        history.value = res.data
        historyTotal.value = res.total
    } catch {
        history.value = []
        historyTotal.value = 0
    } finally {
        historyLoading.value = false
    }
}

/** 续读：优先用持久化句柄（免重选）；否则复用 openPicker（FS Access 优先，不支持时回退 <input>），
 *  选定同一文件（内容 hash 一致）即自动恢复进度。 */
async function continueReading(item: ReadingRecordItem) {
    error.value = ''
    // 1) 本设备有持久化句柄 → 直接读取续读
    const handle = await getFileHandle(item.book_key)
    if (handle) {
        const file = await getFileFromHandle(handle)
        if (file) {
            await openBookFile(file, handle)
            return
        }
    }
    // 2) 无句柄/句柄失效（如 http://IP 非安全上下文无 File System Access API）→
    //    复用 openPicker：支持 FS Access 时用 picker（可重新持久化句柄），
    //    否则回退 <input> 选择器。⚠️ 不能直接调 pickLocalBook()：它在无 FS Access
    //    的环境永远返回 null，会导致点击无任何反应。
    await openPicker()
}

/** 删除阅读记录（仅云端进度；本地文件不受影响） */
async function removeRecord(item: ReadingRecordItem) {
    if (!window.confirm(`删除「${item.title}」的云端阅读记录？本地文件不受影响。`)) return
    try {
        await deleteReadingRecord(item.book_key)
        await deleteFileHandle(item.book_key)
        history.value = history.value.filter(h => h.book_key !== item.book_key)
        historyTotal.value = Math.max(0, historyTotal.value - 1)
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : '删除失败'
    }
}

/** 历史条目进度文案：解析进度位置 + 总数 → 百分比（EPUB=章节序号/PDF=页码/TXT=段落） */
function recordProgressText(item: ReadingRecordItem): string {
    const total = item.progress_total
    if (!item.progress || !total || total <= 0) return '已阅读'
    let current = 0
    try {
        const pos = JSON.parse(item.progress)
        if (typeof pos === 'number') {
            current = item.format === 'txt' ? pos + 1 : Math.min(Math.floor(pos) + 1, total)
        } else if (item.format === 'epub') {
            // epubjs 的 CFI 章节数字 = (spinePos+1)*2（偶数节点序号），章节号 = 数字/2
            const match = /epubcfi\(\/\d+\/(\d+)/.exec(String(pos))
            current = match ? Math.min(Number(match[1]) / 2, total) : 0
        }
    } catch { /* 损坏数据按已阅读处理 */ }
    if (current <= 0) return '已阅读'
    const pct = Math.max(0, Math.min(100, Math.round((current / total) * 100)))
    return `已读 ${pct}%`
}

function formatTime(iso: string): string {
    try {
        const d = new Date(iso)
        const mins = Math.floor((Date.now() - d.getTime()) / 60000)
        if (mins < 1) return '刚刚'
        if (mins < 60) return `${mins} 分钟前`
        const hours = Math.floor(mins / 60)
        if (hours < 24) return `${hours} 小时前`
        const days = Math.floor(hours / 24)
        if (days < 7) return `${days} 天前`
        return d.toLocaleDateString('zh-CN')
    } catch {
        return ''
    }
}

/** 统一开书流程：本地 File → hash(book_key) → 渲染 → 恢复进度（localStorage 本机 + 云端跨设备） */
async function openBookFile(file: File, handle?: FileSystemFileHandle) {
    error.value = ''
    try {
        const bookKey = await hashFile(file)
        if (handle) void saveFileHandle(bookKey, handle)   // 持久化句柄供下次无感续读

        const adapter = createAdapter(file)
        zoom.value = 100   // 新书重置缩放（PDF 专属）
        await adapter.load()                       // 先 load：metadata 才有值
        bookTitle.value = adapter.metadata.title   // 书名现在能显示了
        bookAuthor.value = adapter.metadata.author
        try {
            tocItems.value = await adapter.getToC()    // EPUB 真实目录 / TXT 分段目录 / PDF 大纲
        } catch {
            tocItems.value = []                        // 目录加载失败不阻塞开书
        }
        tocOpen.value = false
        currentBookKey.value = bookKey
        store.setAdapter(adapter, bookKey)  // 设 store：内部从 localStorage 恢复本机进度

        // 云端进度（跨设备权威）：登录且云端有记录时覆盖本机
        if (isLoggedIn.value) {
            try {
                const prog = await getReaderProgress(bookKey)
                const pos = prog.data.position
                if (pos) {
                    try { await adapter.setProgress(JSON.parse(pos)) } catch { /* 格式损坏忽略 */ }
                }
            } catch { /* 404/网络失败：无云端记录，用本机进度 */ }
        }

        await nextTick()                             // 等容器挂载（阅读台在 v-else 分支里）再渲染内容
        if (container.value) await adapter.renderTo(container.value)
        await adapter.setTheme?.(store.settings.bgColor, store.settings.fgColor, {
            lineHeight: store.settings.lineHeight,
            fontFamily: store.settings.fontFamily,
            marginWidth: store.settings.marginWidth,
            indent: store.settings.indent,
        })
        // EPUB 内部翻页（滑动/链接跳转）不经过 next/prev → 注册回调刷新进度并节流保存
        adapter.onProgressChange?.(() => {
            refreshProgress()
            if (progressSaveTimer !== null) return
            progressSaveTimer = window.setTimeout(() => {
                progressSaveTimer = null
                persistProgress()
            }, 1000)
        })
        persistProgress()
        refreshProgress()
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : '打开失败'
        store.setAdapter(null, '')
        currentBookKey.value = ''
    }
}

// EPUB 内部翻页的进度保存节流定时器
let progressSaveTimer: number | null = null

/** 进度保存：localStorage（本机）+ 云端（登录时，按 book_key upsert） */
function persistProgress() {
    store.saveProgress()
    if (isLoggedIn.value && currentBookKey.value && store.adapter) {
        const pos = store.adapter.getProgress()
        void saveReaderProgress({
            book_key: currentBookKey.value,
            title: bookTitle.value || store.adapter.metadata.title || '未命名书籍',
            author: bookAuthor.value || store.adapter.metadata.author,
            format: store.adapter.format,
            progress: JSON.stringify(pos),
            progress_total: store.adapter.getTotal() || null,
        }).catch(() => { /* 静默：网络失败不影响阅读 */ })
    }
}

/** 选书入口：优先 File System Access API（可持久化句柄）；任何失败都回退 <input>，
 *  保证 http://IP 等非安全上下文（无 FS Access）或 API 抛错时仍能选书。
 *  支持多选：打开第一本，其余保存句柄入库（待「书架」迭代展示，同设备可无感续读）。 */
async function openPicker() {
    error.value = ''
    if (isFileSystemAccessSupported()) {
        try {
            const picked = await pickLocalBooks()
            if (picked?.length) {
                await openBookFile(picked[0].file, picked[0].handle)
                for (let i = 1; i < picked.length; i++) {
                    const h = picked[i].handle
                    if (h) void saveFileHandle(picked[i].bookKey, h)
                }
                return
            }
            // 用户取消 → 不打开 input，保持现状
            return
        } catch (e: unknown) {
            // FS Access 异常（SecurityError/NotAllowedError 等，如用户激活过期）→ 静默回退 input，
            // 不打断选书流程；若 input 也失败会在 onFilePicked/openBookFile 中报错
            console.warn('[reader] File System Access 选择失败，回退 <input>:', e)
        }
    }
    fileInput.value?.click()
}

async function onFilePicked(event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files ?? [])
    if (!files.length) return
    input.value = ''                           // 立即重置，允许重复选同一文件
    error.value = ''
    // input 路径拿不到持久化句柄，多选时只打开第一本（其余仅本次会话可读）
    await openBookFile(files[0])
}

async function next() {
    try { await store.adapter?.next() } catch (e: unknown) { error.value = e instanceof Error ? e.message : '翻页失败' }
    persistProgress()
    refreshProgress()
}
async function prev() {
    try { await store.adapter?.prev() } catch (e: unknown) { error.value = e instanceof Error ? e.message : '翻页失败' }
    persistProgress()
    refreshProgress()
}

// ---- 目录抽屉 ----
// 树形目录拍平为带缩进深度的列表，便于渲染多级子目录（EPUB 常见两级）
interface FlatToC {
    id: string
    label: string
    depth: number
    item: ToCItem
}

function flattenToC(items: ToCItem[], depth = 0, out: FlatToC[] = []): FlatToC[] {
    for (const item of items) {
        out.push({ id: item.id, label: item.label, depth, item })
        if (item.subitems?.length) flattenToC(item.subitems, depth + 1, out)
    }
    return out
}

const flatToc = computed<FlatToC[]>(() => flattenToC(tocItems.value))

/**
 * 点击目录项跳转：EPUB 用章节 href（epubjs rendition.display 支持）、
 * TXT 用段落索引（id 形如 p-<段落号>）；PDF 大纲无页码信息，仅作结构展示。
 */
async function jumpTo(item: ToCItem) {
    const adapter = store.adapter
    if (!adapter) return
    try {
        if (adapter.format === 'epub' && item.href) {
            await adapter.setProgress(item.href)
        } else if (adapter.format === 'txt') {
            const match = /^p-(\d+)$/.exec(item.id)
            if (!match) return
            await adapter.setProgress(Number(match[1]))
        } else {
            return
        }
        tocOpen.value = false
        store.saveProgress()
        refreshProgress()
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : '目录跳转失败'
    }
}

// ---- 阅读进度 ----
// 各格式的进度文案：PDF=页码 / TXT=段落数 / EPUB=章节数（从 CFI 解析章节序号）
const positionText = ref('')
const progressPercent = ref(0)
// 当前章节名（EPUB 从 CFI 章节序号近似匹配目录顶层项；TXT/PDF 无章节名）。
// 在 refreshProgress 中同步更新（翻页/内部翻页都会刷新），不做 computed 避免响应性丢失。
const chapterLabel = ref('')

function refreshProgress() {
    const adapter = store.adapter
    if (!adapter) {
        positionText.value = ''
        progressPercent.value = 0
        return
    }
    const totalCount = adapter.getTotal()
    const pos = adapter.getProgress()
    if (adapter.format === 'pdf') {
        const current = typeof pos === 'number' ? Math.max(1, Math.min(Math.floor(pos), totalCount)) : 1
        positionText.value = totalCount > 0 ? `第 ${current} / ${totalCount} 页` : ''
        progressPercent.value = totalCount > 0 ? Math.round(((current - 1) / totalCount) * 100) : 0
    } else if (adapter.format === 'txt') {
        const current = typeof pos === 'number' ? Math.max(0, Math.floor(pos)) : 0
        positionText.value = totalCount > 0 ? `第 ${Math.min(current + 1, totalCount)} / ${totalCount} 段` : ''
        progressPercent.value = totalCount > 0 ? Math.round((Math.min(current, totalCount) / totalCount) * 100) : 0
    } else {
        // EPUB：epubjs 的 CFI 形如 epubcfi(/6/<偶数节点序号>[id]!/...)，章节数字 = (spinePos+1)*2，
        // 章节号 = 数字/2（spinePos 从 0 起，章节从 1 起，故 spinePos+1 = 数字/2）
        const match = /epubcfi\(\/\d+\/(\d+)/.exec(String(pos))
        const chapter = match ? Number(match[1]) / 2 : 0
        positionText.value = totalCount > 0 ? `第 ${Math.min(Math.max(chapter, 1), totalCount)} / ${totalCount} 章` : ''
        progressPercent.value = totalCount > 0 ? Math.round(((Math.min(Math.max(chapter, 1), totalCount) - 1) / totalCount) * 100) : 0
        // 当前章节名：EPUB 用 spine href 匹配目录顶层项（spine 条数≠目录项数，
        // 不能拿章节序号当下标）；TXT/PDF 无章节名。
        // 异步解析，回调里校验 adapter 未变，避免换书后旧标签覆盖新书。
        void Promise.resolve(adapter.getChapterLabel?.(pos) ?? '').then((label) => {
            if (store.adapter === adapter) chapterLabel.value = label
        })
        return
    }
    chapterLabel.value = ''
    progressPercent.value = Math.max(0, Math.min(100, progressPercent.value))
}

// ---- 字体大小调节（PDF 不适用，仅作用于阅读容器文字）----
const FONT_MIN = 12
const FONT_MAX = 28

function changeFontSize(delta: number) {
    store.settings.fontSize = Math.min(FONT_MAX, Math.max(FONT_MIN, store.settings.fontSize + delta))
    // 持久化 + 重排由 settings watch 统一处理（字号变化影响 TXT 分页高度）
}

// ---- 翻页快捷键（←/→ / 空格 / PageUp/PageDown）----
function onKeydown(e: KeyboardEvent) {
    if (!store.adapter) return
    const target = e.target as HTMLElement | null
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault()
        void prev()
    } else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
        e.preventDefault()
        void next()
    }
}

// ---- 滑动翻页（仅 TXT：EPUB 由 epubjs 自带手势；PDF 为滚动浏览不启用）----
let touchStartX = 0
let touchStartY = 0
function onReaderTouchStart(e: TouchEvent) {
    if (store.adapter?.format !== 'txt') return
    touchStartX = e.changedTouches[0].clientX
    touchStartY = e.changedTouches[0].clientY
}
function onReaderTouchEnd(e: TouchEvent) {
    if (store.adapter?.format !== 'txt') return
    const dx = e.changedTouches[0].clientX - touchStartX
    const dy = e.changedTouches[0].clientY - touchStartY
    // 横向位移超阈值且明显大于纵向（排除滚动）才翻页
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx < 0) void next()
        else void prev()
    }
}

// 格式徽标文案
const formatLabel = computed(() => {
    switch (store.adapter?.format) {
        case 'epub': return 'EPUB 电子书'
        case 'pdf': return 'PDF 文档'
        case 'txt': return 'TXT 纯文本'
        default: return ''
    }
})
</script>

<template>
    <div class="max-w-4xl mx-auto px-4 py-8">
        <input ref="fileInput" type="file" accept=".txt,.epub,.pdf" multiple class="hidden" @change="onFilePicked" />

        <!-- 空状态：报纸刊头引导（无书时展示）
             ⚠️ 不用 Transition out-in 包裹：它会让 v-else 阅读台延迟到旧元素离场后才挂载，
             导致 onFilePicked 里 nextTick 后 container 仍为 null、renderTo 被跳过。
             阅读台/空状态自身已有 animate-newsprint-in 入场动画。 -->
        <section v-if="!store.adapter" class="newsprint-texture animate-newsprint-in">
                <div class="text-center pt-6 pb-4">
                    <div class="edition-label text-editorial mb-4">MBookTI · READING DESK 阅读专刊</div>
                    <h1 class="np-hero text-ink dark:text-paper">今日宜读书</h1>
                    <p class="mt-5 font-serif text-lg sm:text-xl italic text-neutral-600 dark:text-neutral-300">
                        「择一册而坐，借半日清闲。铅字有光，常读常新。」
                    </p>
                    <div class="mt-6 flex items-center justify-center gap-3 flex-wrap">
                        <span class="np-badge np-badge-editorial">EPUB</span>
                        <span class="np-badge np-badge-outline">PDF</span>
                        <span class="np-badge np-badge-outline">TXT</span>
                    </div>
                    <div class="ornament-divider">❦</div>

                    <div class="max-w-sm mx-auto np-card hard-shadow p-6 sm:p-8 text-left">
                        <div class="flex items-center gap-2 edition-label text-neutral-500 mb-5">
                            <span class="inline-block w-2 h-2 bg-editorial" aria-hidden="true"></span>
                            开读 · START READING
                        </div>
                        <button class="np-btn np-btn-primary w-full cursor-pointer" @click="openPicker">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                            </svg>
                            选择电子书文件
                        </button>
                        <p class="mt-4 text-center edition-label text-neutral-500 dark:text-neutral-400">
                            文件留本地 · 进度云端同步 · 换设备续读
                        </p>
                    </div>
                </div>

                <!-- 阅读历史：登录用户可见（云端进度记录；文件在本地） -->
                <div v-if="isLoggedIn" class="max-w-2xl mx-auto mt-10 text-left">
                    <div class="flex items-center justify-between border-b-2 border-ink dark:border-paper pb-3 mb-4">
                        <div>
                            <p class="edition-label text-editorial">最近阅读 · RECENT READS</p>
                            <h2 class="font-serif text-xl font-bold text-ink dark:text-paper mt-1">
                                {{ historyTotal }} 本书 · 进度云端同步
                            </h2>
                        </div>
                    </div>

                    <div v-if="historyLoading" class="py-8 text-center edition-label text-neutral-500">
                        阅读记录加载中…
                    </div>

                    <div v-else-if="history.length === 0" class="py-8 text-center border border-dashed border-ink/30 dark:border-paper/30">
                        <p class="font-serif italic text-neutral-500 dark:text-neutral-400">还没有阅读记录，选一本电子书开始吧</p>
                    </div>

                    <ul v-else class="space-y-3">
                        <li
                            v-for="item in history"
                            :key="item.book_key"
                            class="np-card hard-shadow p-4 flex items-center gap-4 hover:border-editorial transition-colors"
                        >
                            <!-- 封面位：无封面文件，显示格式徽标 -->
                            <div class="w-12 h-16 shrink-0 border border-ink dark:border-paper bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center overflow-hidden">
                                <span class="edition-label text-editorial">{{ item.format.toUpperCase() }}</span>
                            </div>
                            <div class="flex-1 min-w-0">
                                <h3 class="font-serif font-semibold text-ink dark:text-paper truncate">{{ item.title }}</h3>
                                <p class="edition-label text-neutral-500 dark:text-neutral-400 mt-1">
                                    {{ item.format.toUpperCase() }} · {{ recordProgressText(item) }} · {{ formatTime(item.updated_at) }}
                                </p>
                            </div>
                            <div class="flex gap-2 shrink-0">
                                <button class="np-btn np-btn-primary !min-h-[32px] !px-3 text-xs cursor-pointer" @click="continueReading(item)">
                                    续读
                                </button>
                                <button class="np-btn np-btn-ghost !min-h-[32px] !px-3 text-xs cursor-pointer" @click="removeRecord(item)">
                                    移除
                                </button>
                            </div>
                        </li>
                    </ul>
                </div>
            </section>

            <!-- 阅读台：报头 + 进度条 + 阅读容器 + 工具栏 -->
            <div
                v-else
                ref="readerRoot"
                class="reader-root animate-newsprint-in"
                :style="{
                    '--reader-bg': store.settings.bgColor,
                    '--reader-font-size': store.settings.fontSize + 'px',
                    '--reader-line-height': String(store.settings.lineHeight),
                    '--reader-font-family': fontFamilyCss(store.settings.fontFamily),
                    '--reader-padding': marginPaddingCss(store.settings.marginWidth),
                    '--reader-indent': store.settings.indent ? '2em' : '0',
                }"
            >
                <header class="border-b-4 border-ink dark:border-paper pb-4 mb-4">
                    <div class="flex items-center justify-between edition-label mb-3">
                        <span class="text-editorial">阅读专刊 · READING DESK</span>
                        <div class="flex items-center gap-4">
                            <span class="text-neutral-500 dark:text-neutral-400 hidden sm:inline">{{ formatLabel }}</span>
                            <button class="np-btn np-btn-ghost !min-h-[30px] !px-3 text-[10px]" @click="openPicker">换一本</button>
                        </div>
                    </div>
                    <h1 class="font-serif font-black text-3xl sm:text-4xl leading-tight break-words text-ink dark:text-paper">
                        {{ bookTitle }}
                    </h1>
                    <div class="mt-3 flex items-center gap-3 flex-wrap">
                        <span class="font-serif italic text-neutral-600 dark:text-neutral-300">作者 · {{ bookAuthor }}</span>
                        <span class="np-badge np-badge-outline">{{ formatLabel }}</span>
                    </div>
                </header>

                <!-- 阅读进度：页码/章节 + 当前章节名 + 进度条 -->
                <div class="flex items-center gap-3 mb-3">
                    <span class="np-badge np-badge-outline shrink-0">{{ positionText }}</span>
                    <span v-if="chapterLabel" class="font-serif text-sm text-neutral-600 dark:text-neutral-300 truncate">
                        {{ chapterLabel }}
                    </span>
                    <div
                        class="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-600"
                        role="progressbar"
                        :aria-valuenow="progressPercent"
                        aria-valuemin="0"
                        aria-valuemax="100"
                    >
                        <div
                            class="h-full bg-editorial transition-all duration-300"
                            :style="{ width: progressPercent + '%' }"
                        ></div>
                    </div>
                </div>

                <!-- 阅读容器（外框：硬阴影报纸剪贴感，背景跟随用户设置） -->
                <div class="reader-frame relative border border-ink dark:border-paper hard-shadow">
                    <div
                        ref="container"
                        class="reader-container h-[70vh] overflow-hidden"
                        @touchstart="onReaderTouchStart"
                        @touchend="onReaderTouchEnd"
                    ></div>
                    <!-- 点击分区翻页（仅 TXT，桌面端）：左 1/3 上一页、右 2/3（含中央）下一页、无死区，
                         与 EPUB 的 iframe 内监听规则完全一致；
                         EPUB 不渲染覆盖层——epubjs iframe 内部已做分区翻页且放行书内链接/目录，
                         覆盖层会挡在 iframe 上方导致书内链接点不动；
                         PDF 不渲染覆盖层——需保留滚动条/滚轮操作，覆盖层会拦截滚动；
                         移动端用滑动翻页，隐藏热区避免误触 -->
                    <div v-if="store.adapter?.format === 'txt'" class="absolute inset-0 z-20 hidden sm:flex" aria-hidden="true">
                        <div class="w-1/3 h-full cursor-w-resize" @click="prev"></div>
                        <div class="w-2/3 h-full cursor-e-resize" @click="next"></div>
                    </div>
                </div>

                <!-- 工具栏 -->
                <div class="reader-toolbar mt-4 border border-ink dark:border-paper bg-paper dark:bg-[#201f16] p-2 sm:p-3 flex flex-wrap items-center gap-2">
                    <!-- 目录 -->
                    <button v-if="tocItems.length > 0" class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="tocOpen = !tocOpen">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h10" />
                        </svg>
                        {{ tocOpen ? '收起目录' : '目录' }}
                    </button>

                    <!-- 上一页 / 下一页 -->
                    <button class="np-btn np-btn-primary !min-h-[36px] px-4 text-xs" @click="prev">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                        </svg>
                        上一页
                    </button>
                    <button class="np-btn np-btn-secondary !min-h-[36px] px-4 text-xs" @click="next">
                        下一页
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                    </button>

                    <div class="w-px h-6 bg-ink/20 dark:bg-paper/30 hidden sm:block" aria-hidden="true"></div>

                    <!-- 字体调节（PDF 无字体概念） -->
                    <div v-if="!isPdf" class="flex items-center gap-1" title="阅读字号">
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="changeFontSize(-1)" aria-label="减小字号">A−</button>
                        <span class="font-mono text-xs text-neutral-500 dark:text-neutral-400 min-w-[2.5rem] text-center">{{ store.settings.fontSize }}</span>
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="changeFontSize(1)" aria-label="增大字号">A+</button>
                    </div>

                    <!-- PDF 缩放 -->
                    <div v-if="isPdf" class="flex items-center gap-1" title="页面缩放">
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="zoomOut" aria-label="缩小">−</button>
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs min-w-[3.5rem]" @click="resetZoom" title="重置为适配宽度">{{ zoom }}%</button>
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="zoomIn" aria-label="放大">＋</button>
                    </div>

                    <div class="w-px h-6 bg-ink/20 dark:bg-paper/30 hidden sm:block" aria-hidden="true"></div>

                    <!-- 背景色 -->
                    <div class="relative">
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="showColors = !showColors">背景色</button>
                        <div v-if="showColors" class="fixed inset-0 z-20" @click="showColors = false"></div>
                        <div v-if="showColors" class="absolute right-0 bottom-full mb-2 z-30 w-60 border border-ink dark:border-paper bg-paper dark:bg-[#201f16] hard-shadow p-4">
                            <p class="edition-label text-neutral-500 mb-3">页面色调 · PAGE TONE</p>
                            <div class="flex gap-2 flex-wrap">
                                <button
                                    v-for="c in PRESET_COLORS"
                                    :key="c.bg"
                                    class="w-9 h-9 border border-ink/30 cursor-pointer hover:border-editorial transition-colors"
                                    :style="{ backgroundColor: c.bg }"
                                    :title="c.name"
                                    @click="applyColors(c.bg, c.fg)"
                                ></button>
                            </div>
                            <div class="mt-4 flex items-center gap-2 border-t border-ink/10 dark:border-paper/20 pt-3">
                                <input type="color" class="w-9 h-9 p-0 border border-ink/30 cursor-pointer" :value="store.settings.bgColor" @input="onCustomColor" />
                                <span class="text-xs font-mono text-neutral-500 dark:text-neutral-400">自定义背景</span>
                            </div>
                        </div>
                    </div>

                    <!-- 排版（字体 / 行距 / 页边距 / 首行缩进） -->
                    <div class="relative">
                        <button class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs" @click="showTypo = !showTypo">排版</button>
                        <div v-if="showTypo" class="fixed inset-0 z-20" @click="showTypo = false"></div>
                        <div v-if="showTypo" class="absolute right-0 bottom-full mb-2 z-30 w-64 border border-ink dark:border-paper bg-paper dark:bg-[#201f16] hard-shadow p-4">
                            <p class="edition-label text-neutral-500 mb-3">排版 · TYPOGRAPHY</p>

                            <!-- 字体 -->
                            <p class="edition-label text-neutral-400 mb-1.5">字体</p>
                            <div class="flex gap-1 mb-4">
                                <button
                                    v-for="f in FONT_OPTIONS"
                                    :key="f.value"
                                    @click="store.settings.fontFamily = f.value"
                                    class="flex-1 px-2 py-1 text-xs border cursor-pointer transition-colors"
                                    :class="store.settings.fontFamily === f.value
                                        ? 'border-editorial bg-paper text-editorial'
                                        : 'border-ink/20 text-neutral-500 hover:border-ink dark:border-paper/20 dark:text-neutral-300 dark:hover:border-paper'"
                                >{{ f.label }}</button>
                            </div>

                            <!-- 行距 -->
                            <p class="edition-label text-neutral-400 mb-1.5">行距</p>
                            <div class="flex gap-1 mb-4">
                                <button
                                    v-for="lh in LINE_OPTIONS"
                                    :key="lh.value"
                                    @click="store.settings.lineHeight = lh.value"
                                    class="flex-1 px-2 py-1 text-xs border cursor-pointer transition-colors"
                                    :class="store.settings.lineHeight === lh.value
                                        ? 'border-editorial bg-paper text-editorial'
                                        : 'border-ink/20 text-neutral-500 hover:border-ink dark:border-paper/20 dark:text-neutral-300 dark:hover:border-paper'"
                                >{{ lh.label }}</button>
                            </div>

                            <!-- 页边距 -->
                            <p class="edition-label text-neutral-400 mb-1.5">页边距</p>
                            <div class="flex gap-1 mb-4">
                                <button
                                    v-for="m in MARGIN_OPTIONS"
                                    :key="m.value"
                                    @click="store.settings.marginWidth = m.value"
                                    class="flex-1 px-2 py-1 text-xs border cursor-pointer transition-colors"
                                    :class="store.settings.marginWidth === m.value
                                        ? 'border-editorial bg-paper text-editorial'
                                        : 'border-ink/20 text-neutral-500 hover:border-ink dark:border-paper/20 dark:text-neutral-300 dark:hover:border-paper'"
                                >{{ m.label }}</button>
                            </div>

                            <!-- 首行缩进 -->
                            <label class="flex items-center justify-between border border-ink/15 dark:border-paper/20 px-3 py-2.5 cursor-pointer">
                                <span class="text-xs font-medium text-ink dark:text-paper">首行缩进</span>
                                <span class="relative inline-flex items-center h-5 w-9 shrink-0 rounded-full transition-colors"
                                    :class="store.settings.indent ? 'bg-editorial' : 'bg-neutral-300 dark:bg-neutral-600'">
                                    <input type="checkbox" v-model="store.settings.indent" class="sr-only" />
                                    <span class="inline-block w-3.5 h-3.5 bg-paper rounded-full shadow transition-transform"
                                        :class="store.settings.indent ? 'translate-x-[18px]' : 'translate-x-0.5'"></span>
                                </span>
                            </label>
                        </div>
                    </div>

                    <!-- 全屏 -->
                    <button v-if="fullscreenSupported" class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs ml-auto" @click="toggleFullscreen">
                        <svg v-if="!isFullscreen" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                        </svg>
                        <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4m0 0H4m5 0L4 9m11 6v5m0 0h5m-5 0l5-5M4 15v5m0 0h5m-5 0l5-5" />
                        </svg>
                        {{ isFullscreen ? '退出全屏' : '全屏' }}
                    </button>
                </div>

                <!-- 目录抽屉：覆盖在阅读台上（全屏时随 readerRoot 一起进入全屏） -->
                <Transition name="toc-fade">
                    <div v-if="tocOpen" class="fixed inset-0 z-40 bg-ink/50 dark:bg-black/60" @click="tocOpen = false"></div>
                </Transition>
                <Transition name="toc-slide">
                    <aside
                        v-if="tocOpen"
                        class="toc-drawer fixed top-0 left-0 bottom-0 z-50 w-80 max-w-[85vw] border-r-4 border-ink dark:border-paper bg-paper dark:bg-[#201f16] flex flex-col shadow-[8px_0_0_0_rgba(17,17,17,0.15)] dark:shadow-[8px_0_0_0_rgba(249,249,247,0.2)]"
                    >
                        <header class="border-b-2 border-ink dark:border-paper px-4 py-3 flex items-center justify-between gap-3 shrink-0">
                            <div class="min-w-0">
                                <p class="edition-label text-editorial">目录 · CONTENTS</p>
                                <h2 class="font-serif font-bold text-lg text-ink dark:text-paper mt-1 truncate">{{ bookTitle }}</h2>
                            </div>
                            <button class="np-btn np-btn-ghost !min-h-[32px] !min-w-[32px] !p-0 w-8 h-8 shrink-0" @click="tocOpen = false" aria-label="关闭目录">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </header>
                        <nav class="flex-1 overflow-y-auto py-2">
                            <button
                                v-for="entry in flatToc"
                                :key="entry.item.id"
                                class="toc-entry flex items-center gap-2 w-full text-left px-4 py-2.5 text-sm border-b border-divider dark:border-paper/15 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors"
                                :class="entry.depth === 0 ? 'font-serif font-semibold text-ink dark:text-paper' : 'text-neutral-600 dark:text-neutral-300'"
                                :style="{ paddingLeft: (12 + entry.depth * 16) + 'px' }"
                                @click="jumpTo(entry.item)"
                            >
                                <span class="toc-seq font-mono text-[10px] text-editorial shrink-0">{{ String(entry.depth + 1).padStart(2, '0') }}</span>
                                <span class="min-w-0 truncate">{{ entry.label }}</span>
                            </button>
                        </nav>
                        <footer class="border-t border-ink/10 dark:border-paper/20 px-4 py-2 edition-label text-neutral-500 dark:text-neutral-400 text-[10px] shrink-0">
                            点击条目跳转至对应位置
                        </footer>
                    </aside>
                </Transition>
            </div>

        <!-- 错误提示 -->
        <p v-if="error" class="mt-4 text-center font-mono text-sm text-editorial border border-editorial/40 bg-paper dark:bg-[#201f16] px-4 py-2">
            {{ error }}
        </p>
    </div>
</template>

<style scoped>
.reader-root {
    display: flex;
    flex-direction: column;
}

/* 阅读区外框：硬阴影报纸剪贴感；背景跟随用户设置的自定义背景色 */
.reader-frame {
    background: var(--reader-bg, #fff);
}

/* 阅读容器：页边距由排版设置控制（EPUB iframe 被压缩出留白 / TXT 段落区收缩） */
.reader-container {
    padding: var(--reader-padding, 1.25rem 2rem);
}

/* TXT 段落排版（adapter 动态生成的 p 元素，需 :deep 穿透）；
   字体/行距/首行缩进跟随排版设置（--reader-* 变量），最大行宽限制成报纸栏宽，
   翻页时新段落整体淡入（转场动画） */
.reader-container :deep(p) {
    font-family: var(--reader-font-family, var(--font-body));
    font-size: var(--reader-font-size, 16px);
    line-height: var(--reader-line-height, 1.9);
    text-indent: var(--reader-indent, 0);
    max-width: 42rem;
    margin: 0 auto 1.1em;
    padding: 0 1.25rem;
    text-align: justify;
    overflow-wrap: break-word;
    animation: reader-fade-in 0.25s ease;
}
.reader-container :deep(p:last-child) {
    margin-bottom: 0;
}

/* 翻页转场：TXT 重绘时段落淡入（EPUB 由 epubjs 自带翻页过渡） */
@keyframes reader-fade-in {
    from { opacity: 0; transform: translateY(3px); }
    to { opacity: 1; transform: none; }
}

/* 目录抽屉滑动动画（报纸侧栏硬切入） */
.toc-fade-enter-active,
.toc-fade-leave-active {
    transition: opacity 0.2s ease-out;
}
.toc-fade-enter-from,
.toc-fade-leave-to {
    opacity: 0;
}
.toc-slide-enter-active,
.toc-slide-leave-active {
    transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
.toc-slide-enter-from,
.toc-slide-leave-to {
    transform: translateX(-100%);
}

/* 全屏时：外层占满视口，阅读容器吃掉剩余高度（报头/工具栏保留自然高度）
   背景跟随用户设置的自定义背景色 */
.reader-root:fullscreen {
    width: 100vw;
    height: 100vh;
    background: var(--reader-bg, #fff);
    padding: 1rem;
    overflow-y: auto;
}
.reader-root:fullscreen .reader-frame {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}
.reader-root:fullscreen .reader-container {
    flex: 1;
    height: auto;
    min-height: 0;
}
</style>
