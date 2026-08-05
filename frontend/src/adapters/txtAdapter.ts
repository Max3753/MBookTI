import jschardet from 'jschardet'
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition, ReaderTypography } from './types'

// 字体栈：与 EPUB 注入的规则一致（TXT 段落渲染在阅读器容器内，靠继承生效）
const FONT_STACKS: Record<NonNullable<ReaderTypography['fontFamily']>, string | null> = {
    default: null,
    serif: "'Songti SC', 'SimSun', 'Noto Serif CJK SC', Georgia, 'Times New Roman', serif",
    sans: "'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Helvetica Neue', Arial, sans-serif",
}

// 一页 = 一段连续的段落范围（含两端）。进度仍以「段落索引」持久化，
// 与旧存档（reader_progress_* 存的数字）完全兼容，无需迁移。
interface PageRange {
    start: number
    end: number
}

export function createTxtAdapter(file: File): IBookAdapter {
    let paragraphs: string[] = []
    let pages: PageRange[] = []
    let currentPage = 0
    let container: HTMLElement | null = null
    let title = file.name.replace(/\.txt$/i, '')

    // 元数据（接口要求
    const metadata: BookMetadata = { title, author: '未知作者'}

    async function load() {
        const buffer = await file.arrayBuffer()
        const u8 = new Uint8Array(buffer)

        // jschardet 需要二进制字符串（每个字符=一个字节），不能直接传 Uint8Array
        // 取前 64KB 检测编码即可，不用全文
        const sample = u8.slice(0, 65536)
        let binary = ''
        for (let i = 0; i < sample.length; i++) {
            binary += String.fromCharCode(sample[i])
        }
        const detected = jschardet.detect(binary)

        const text = new TextDecoder(detected.encoding || 'utf-8').decode(u8)
        paragraphs = text.split(/\r?\n/).filter(p => p.trim() !== '')
    }
    // ... getToC / rederTo / next / prev / getProgress / setProgress / destroy
    function getToC(): Promise<ToCItem[]> {
        // 简单实现：每 50 段一个目录项（真正的章节识别很复杂，MVP 够用）
        const items: ToCItem[] = []
        for (let i = 0; i < paragraphs.length; i += 50) {
            items.push({
                id: `p-${i}`,
                label: paragraphs[i].slice(0, 30),
                href: undefined,
                subitems: [],
            })
        }
        return Promise.resolve(items)
    }

    /**
     * 按容器可视高度把段落切成「一页多段」。
     * 逐段 append 后检测 scrollHeight 溢出，溢出处即为页边界。
     * 计算期间临时隐藏容器，避免中间状态闪烁。
     */
    function computePages() {
        pages = []
        if (!container || paragraphs.length === 0) return

        const prevVisibility = container.style.visibility
        container.style.visibility = 'hidden'
        container.innerHTML = ''

        const height = container.clientHeight
        let start = 0
        for (let i = 0; i < paragraphs.length; i++) {
            const p = document.createElement('p')
            p.textContent = paragraphs[i]  // textContent 防 XSS
            container.appendChild(p)

            if (container.scrollHeight > height + 1) {
                if (i === start) {
                    // 单段就超高（超长段）：独占一页，强制推进避免死循环
                    pages.push({ start: i, end: i })
                    container.innerHTML = ''
                    start = i + 1
                } else {
                    // 本段放不下：前一段为止成一页，本段开新页
                    pages.push({ start, end: i - 1 })
                    container.innerHTML = ''
                    const next = document.createElement('p')
                    next.textContent = paragraphs[i]
                    container.appendChild(next)
                    start = i
                }
            }
        }
        if (start < paragraphs.length) {
            pages.push({ start, end: paragraphs.length - 1 })
        }

        container.style.visibility = prevVisibility
    }

    /** 找包含指定段落的页；找不到返回最后一页 */
    function locatePage(paraIndex: number): number {
        for (let i = 0; i < pages.length; i++) {
            if (paraIndex >= pages[i].start && paraIndex <= pages[i].end) return i
        }
        return pages.length > 0 ? pages.length - 1 : 0
    }

    function renderCurrent() {
        if (!container) return
        const page = pages[currentPage]
        if (!page) return
        container.innerHTML = ''
        const frag = document.createDocumentFragment()
        for (let i = page.start; i <= page.end; i++) {
            const p = document.createElement('p')
            p.textContent = paragraphs[i] ?? ''  // textContent 防 XSS
            frag.appendChild(p)
        }
        container.appendChild(frag)
    }

    function renderTo(element: HTMLElement) {
        container = element
        computePages()
        if (pendingIndex !== null && pendingIndex < paragraphs.length) {
            currentPage = locatePage(pendingIndex)
            pendingIndex = null
        }
        renderCurrent()
    }

    function getProgress(): ProgressPosition {
        return pages[currentPage]?.start ?? 0
    }

    function getTotal(): number {
        return paragraphs.length
    }

    let pendingIndex: number | null = null

    // 进度 = 段落索引（页首段）；旧存档数字直接兼容
    function setProgress(position: ProgressPosition) {
        if (typeof position !== 'number' || position < 0) return
        if (pages.length === 0) {
            pendingIndex = position        // 还没渲染过，暂存，renderTo 时应用
        } else if (position < paragraphs.length) {
            currentPage = locatePage(position)
            renderCurrent()
        }
    }

    function next() {
        if (currentPage < pages.length - 1) {
            currentPage++
            renderCurrent()
        }
    }

    function prev() {
        if (currentPage > 0) {
            currentPage--
            renderCurrent()
        }
    }

    // 容器尺寸变化（全屏/窗口 resize）后重排：保持当前页首段锚点不变
    function relayout() {
        if (!container) return
        const anchor = pages[currentPage]?.start ?? 0
        computePages()
        currentPage = locatePage(anchor)
        renderCurrent()
    }

    // 应用背景/文字色 + 排版（样式在容器上，renderCurrent 重建内容不影响）。
    // 行距/字体设容器样式由段落继承；缩进与页边距由阅读器 CSS 变量控制（.reader-container 规则）。
    function setTheme(bgColor: string, fgColor: string, typo?: ReaderTypography) {
        if (!container) return
        container.style.backgroundColor = bgColor
        container.style.color = fgColor
        if (typo) {
            container.style.lineHeight = String(typo.lineHeight)
            container.style.fontFamily = FONT_STACKS[typo.fontFamily] ?? ''
        }
    }

    function destroy() {
        container = null   // 断开引用，便于 GC
    }

    return {
        metadata,
        format: 'txt',
        load,
        getToC,
        getProgress,
        setProgress,
        renderTo,
        next,
        prev,
        relayout,
        setTheme,
        destroy,
        getTotal
    }
}
