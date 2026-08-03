import jschardet from 'jschardet'
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition } from './types'

export function createTxtAdapter(file: File): IBookAdapter {
    let paragraphs: string[] = []
    let currentIndex = 0
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

    function renderTo(element: HTMLElement) {
        container = element
        renderCurrent()
    }

    function renderCurrent() {
        if (!container) return
        // 只渲染当前段落（配合上下键/点击翻段；虚拟滚动后续优化）
        container.innerHTML = ''
        const p = document.createElement('p')
        p.textContent = paragraphs[currentIndex] ?? ''  // textContent 防 XSS
        container.appendChild(p)
    }

    function getProgress(): ProgressPosition {
        return currentIndex
    }

    function getTotal(): number {
        return paragraphs.length
    }

    let pendingIndex: number | null = null

    // setProgress 改为：
    function setProgress(position: ProgressPosition) {
        if (typeof position !== 'number' || position < 0) return
        if (position < paragraphs.length) {
            currentIndex = position
            renderCurrent()
        } else {
            pendingIndex = position        // 段落还没加载完，暂存
        }
    }

    // load() 末尾追加（加载完成后应用暂存进度）：
    if (pendingIndex !== null && pendingIndex < paragraphs.length) {
        currentIndex = pendingIndex
        pendingIndex = null
    }

    function next() {
        if (currentIndex < paragraphs.length - 1) {
            currentIndex++
            renderCurrent()
        }
    }

    function prev() {
        if (currentIndex > 0) {
            currentIndex--
            renderCurrent()
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
        destroy,
        getTotal
    }
}
