import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition } from './types'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// PDF 适配器：基于 pdfjs-dist（懒加载，worker 用 ?url 交给 Vite 打包为独立 asset）。
// 进度 = 页码（number，与 TXT 同属页码进度，直接兼容存档）。
// 页面按容器宽度等比缩放（含 devicePixelRatio 提升清晰度），超高页在容器内滚动。
// 缩放：zoom 百分比（100 = 适配容器宽度），放大后容器双向滚动。
export function createPdfAdapter(file: File): IBookAdapter {
    let pdfjs: typeof import('pdfjs-dist') | null = null
    let pdfDoc: PDFDocumentProxy | null = null
    let container: HTMLElement | null = null
    let canvas: HTMLCanvasElement | null = null
    let renderTask: RenderTask | null = null
    let currentPage = 1
    let pendingPage: number | null = null
    let zoom = 100   // 缩放百分比：100 = 适配容器宽度
    const metadata: BookMetadata = {
        title: file.name.replace(/\.pdf$/i, ''),
        author: '未知作者',
    }

    async function load() {
        pdfjs = await import('pdfjs-dist')
        pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
        const data = new Uint8Array(await file.arrayBuffer())
        pdfDoc = await pdfjs.getDocument({ data }).promise
        // 尝试读取 PDF 内置标题，失败（无元数据/解析异常）则用文件名
        try {
            const meta = await pdfDoc.getMetadata()
            const title = (meta.info as { Title?: string }).Title
            if (title) metadata.title = title
        } catch { /* 忽略：部分 PDF 无元数据 */ }
    }

    type OutlineNode = NonNullable<Awaited<ReturnType<PDFDocumentProxy['getOutline']>>>[number]

    function toTocItem(node: OutlineNode, path: string): ToCItem {
        return {
            id: path,
            label: node.title ?? '',
            href: undefined,
            subitems: node.items?.map((child, j) => toTocItem(child, `${path}-${j}`)) ?? [],
        }
    }

    async function getToC(): Promise<ToCItem[]> {
        const outline = await pdfDoc?.getOutline()
        if (!outline) return []
        return outline.map((node, i) => toTocItem(node, `pdf-toc-${i}`))
    }

    async function renderTo(element: HTMLElement) {
        container = element
        element.innerHTML = ''
        element.style.overflow = 'auto'   // PDF 放大后页面超高/超宽，容器内双向滚动（其余格式为 hidden）
        canvas = document.createElement('canvas')
        canvas.style.display = 'block'
        canvas.style.cursor = 'pointer'   // 提示可点击翻页
        element.appendChild(canvas)
        if (pdfDoc && pendingPage !== null) {
            if (pendingPage >= 1 && pendingPage <= pdfDoc.numPages) currentPage = pendingPage
            pendingPage = null
        }
        // 桌面端点击分区翻页（不遮挡滚动条/滚轮，滚动优先；canvas 本身可滚动容器内滚动）：
        // 左 1/3 → 上一页，右 2/3（含中央）→ 下一页，与 TXT/EPUB 规则一致。
        // 位移判定：拖选/拖滚动后松手不翻页；250ms 锁防连点并发渲染抖动。
        const startPos = { x: 0, y: 0 }
        let lastTurnAt = 0
        canvas.addEventListener('mousedown', (e: MouseEvent) => {
            startPos.x = e.clientX
            startPos.y = e.clientY
        })
        canvas.addEventListener('click', (e: MouseEvent) => {
            const now = Date.now()
            if (now - lastTurnAt < 250) return
            if (Math.abs(e.clientX - startPos.x) + Math.abs(e.clientY - startPos.y) > 8) return
            const c = canvas
            if (!c) return
            const rect = c.getBoundingClientRect()
            const x = e.clientX - rect.left
            if (x < rect.width / 3) {
                lastTurnAt = now
                void prev()
            } else {
                lastTurnAt = now
                void next()
            }
        })
        await renderCurrent()
    }

    async function renderCurrent() {
        if (!container || !pdfDoc || !canvas) return
        if (renderTask) { renderTask.cancel(); renderTask = null }   // 取消上一页渲染（触发旧 promise reject）
        const page = await pdfDoc.getPage(currentPage)
        const width = container.clientWidth || 800
        const dpr = window.devicePixelRatio || 1
        // CSS 宽度 = 容器宽 × 缩放比；位图像素再乘 dpr 保证清晰
        const cssWidth = width * (zoom / 100)
        const scale = (cssWidth / page.getViewport({ scale: 1 }).width) * dpr
        const viewport = page.getViewport({ scale })
        canvas.width = Math.floor(viewport.width)
        canvas.height = Math.floor(viewport.height)
        canvas.style.width = `${cssWidth}px`
        canvas.style.height = 'auto'   // 保持宽高比
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        const task = page.render({ canvasContext: ctx, viewport })
        renderTask = task
        try {
            await task.promise
        } catch (e) {
            // 被 cancel（翻页/销毁触发的新渲染）→ 静默；其余真实错误上抛
            if (renderTask !== task) return
            throw e
        } finally {
            if (renderTask === task) renderTask = null
        }
    }

    function getProgress(): ProgressPosition {
        return currentPage
    }

    function getTotal(): number {
        return pdfDoc?.numPages ?? 0
    }

    async function setProgress(position: ProgressPosition) {
        if (typeof position !== 'number') return
        if (!pdfDoc) { pendingPage = position; return }
        if (position >= 1 && position <= pdfDoc.numPages) {
            currentPage = Math.floor(position)
            await renderCurrent()
        }
    }

    async function next() {
        if (pdfDoc && currentPage < pdfDoc.numPages) {
            currentPage++
            await renderCurrent()
            progressListener?.()
        }
    }

    async function prev() {
        if (currentPage > 1) {
            currentPage--
            await renderCurrent()
            progressListener?.()
        }
    }

    // 内部翻页（canvas 点击分区翻页）后通知阅读器刷新进度文案
    let progressListener: (() => void) | null = null
    function onProgressChange(listener: () => void) {
        progressListener = listener
    }

    // 容器尺寸变化（全屏/窗口 resize）：按新宽度重渲染当前页（保持当前缩放）
    async function relayout() {
        await renderCurrent()
    }

    // 缩放百分比（50–200）：重渲染当前页
    async function setZoom(percent: number) {
        const clamped = Math.min(200, Math.max(50, Math.round(percent)))
        if (clamped === zoom) return
        zoom = clamped
        await renderCurrent()
    }

    function destroy() {
        if (renderTask) { renderTask.cancel(); renderTask = null }
        if (pdfDoc) { void pdfDoc.destroy().catch(() => { /* 释放期错误忽略 */ }) }
        pdfDoc = null
        canvas = null
        container = null
    }

    return {
        metadata, format: 'pdf', load, getToC,
        getProgress, getTotal, setProgress, renderTo,
        next, prev, relayout, setZoom, onProgressChange, destroy,
    }
}
