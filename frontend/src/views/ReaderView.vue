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
    pickLocalBook,
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

// 背景/文字色变更 → 应用到当前书
watch(() => [store.settings.bgColor, store.settings.fgColor] as const, ([bg, fg]) => {
    void store.adapter?.setTheme?.(bg, fg)
})

onMounted(() => {
    store.loadSettings()   // 恢复持久化的阅读设置
    if (isLoggedIn.value) void loadHistory()
})

// 离开阅读器时清理内存态：store.adapter 是全局单例，若不清理，
// 从个人主页等页面 SPA 跳回 /reader 时会直接渲染阅读台（且容器空白，
// 因为 onMounted 不再重新 renderTo），而不是空态主页；刷新后才会正常。
// 进度已持久化（localStorage + 云端），下次选同一文件会自动续读，不影响。
onUnmounted(() => {
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

/** 续读：优先用持久化句柄（免重选）；否则打开选择器，选同一文件后按 book_key 自动续读 */
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
    // 2) 无句柄/句柄失效 → 打开选择器让用户重选（选定后 hash 一致即自动恢复进度）
    const picked = await pickLocalBook().catch(() => null)
    if (!picked) return
    await openBookFile(picked.file, picked.handle)
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
            const match = /epubcfi\(\/\d+\/(\d+)/.exec(String(pos))
            current = match ? Math.min(Number(match[1]) + 1, total) : 0
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
        await adapter.setTheme?.(store.settings.bgColor, store.settings.fgColor)  // 应用当前背景色
        persistProgress()
        refreshProgress()
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : '打开失败'
        store.setAdapter(null, '')
        currentBookKey.value = ''
    }
}

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

/** 选书入口：优先 File System Access API（可持久化句柄）；否则回退 <input> */
async function openPicker() {
    error.value = ''
    if (isFileSystemAccessSupported()) {
        try {
            const picked = await pickLocalBook()
            if (!picked) return   // 用户取消
            await openBookFile(picked.file, picked.handle)
            return
        } catch (e: unknown) {
            error.value = e instanceof Error ? e.message : '打开文件失败'
            return
        }
    }
    fileInput.value?.click()
}

async function onFilePicked(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    input.value = ''                           // 立即重置，允许重复选同一文件
    error.value = ''
    await openBookFile(file)
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
        // EPUB：epubjs 的 CFI 形如 epubcfi(/6/<章节序号>[id]!/...)，解析序号换算当前章
        const match = /epubcfi\(\/\d+\/(\d+)/.exec(String(pos))
        const chapter = match ? Number(match[1]) + 1 : 0
        positionText.value = totalCount > 0 ? `第 ${Math.min(Math.max(chapter, 1), totalCount)} / ${totalCount} 章` : ''
        progressPercent.value = totalCount > 0 ? Math.round(((Math.min(Math.max(chapter, 1), totalCount) - 1) / totalCount) * 100) : 0
    }
    progressPercent.value = Math.max(0, Math.min(100, progressPercent.value))
}

// ---- 字体大小调节（PDF 不适用，仅作用于阅读容器文字）----
const FONT_MIN = 12
const FONT_MAX = 28

function changeFontSize(delta: number) {
    store.settings.fontSize = Math.min(FONT_MAX, Math.max(FONT_MIN, store.settings.fontSize + delta))
    store.saveSettings()
    // 字号变化影响 TXT 分页高度 → 等 DOM 应用新字号后重排，保持当前段落锚点；EPUB/PDF 无副作用
    nextTick(() => {
        void store.adapter?.relayout?.()
        refreshProgress()
    })
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
        <input ref="fileInput" type="file" accept=".txt,.epub,.pdf" class="hidden" @change="onFilePicked" />

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
                :style="{ '--reader-bg': store.settings.bgColor, '--reader-font-size': store.settings.fontSize + 'px' }"
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

                <!-- 阅读进度：页码/章节 + 进度条 -->
                <div class="flex items-center gap-3 mb-3">
                    <span class="np-badge np-badge-outline shrink-0">{{ positionText }}</span>
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
                <div class="reader-frame border border-ink dark:border-paper hard-shadow">
                    <div ref="container" class="reader-container h-[70vh] overflow-hidden"></div>
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

/* TXT 段落排版（adapter 动态生成的 p 元素，需 :deep 穿透）；
   字体沿用设计系统衬线正文，最大行宽限制成报纸栏宽，便于阅读 */
.reader-container :deep(p) {
    font-family: var(--font-body);
    font-size: var(--reader-font-size, 16px);
    line-height: 1.9;
    max-width: 42rem;
    margin: 0 auto 1.1em;
    padding: 0 1.25rem;
    text-align: justify;
    overflow-wrap: break-word;
}
.reader-container :deep(p:last-child) {
    margin-bottom: 0;
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
