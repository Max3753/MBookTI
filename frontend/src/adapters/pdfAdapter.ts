import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition } from './types'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// PDF 适配器：基于 pdfjs-dist（懒加载，worker 用 ?url 交给 Vite 打包为独立 asset）。
// 进度 = 页码（number，与 TXT 同属数字进度，直接兼容存档）。
// 页面按容器宽度等比缩放（含 devicePixelRatio 提升清晰度），超高页在容器内滚动。
export function createPdfAdapter(file: File): IBookAdapter {
    let pdfjs: typeof import('pdfjs-dist') | null = null
    let pdfDoc: PDFDocumentProxy | null = null
    let container: HTMLElement | null = null
    let canvas: HTMLCanvasElement | null = null
    let renderTask: RenderTask | null = null
    let currentPage = 1
    let pendingPage: number | null = null
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
        element.style.overflowY = 'auto'   // PDF 页面超高时容器内滚动（其余格式为 hidden）
        canvas = document.createElement('canvas')
        canvas.style.display = 'block'
        canvas.style.width = '100%'
        element.appendChild(canvas)
        if (pdfDoc && pendingPage !== null) {
            if (pendingPage >= 1 && pendingPage <= pdfDoc.numPages) currentPage = pendingPage
            pendingPage = null
        }
        await renderCurrent()
    }

    async function renderCurrent() {
        if (!container || !pdfDoc || !canvas) return
        if (renderTask) { renderTask.cancel(); renderTask = null }   // 取消上一页渲染（触发旧 promise reject）
        const page = await pdfDoc.getPage(currentPage)
        const width = container.clientWidth || 800
        const dpr = window.devicePixelRatio || 1
        const scale = (width / page.getViewport({ scale: 1 }).width) * dpr
        const viewport = page.getViewport({ scale })
        canvas.width = Math.floor(viewport.width)
        canvas.height = Math.floor(viewport.height)
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
        }
    }

    async function prev() {
        if (currentPage > 1) {
            currentPage--
            await renderCurrent()
        }
    }

    // 容器尺寸变化（全屏/窗口 resize）：按新宽度重渲染当前页
    async function relayout() {
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
        next, prev, relayout, destroy,
    }
}
