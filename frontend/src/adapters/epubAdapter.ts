// EPUB 适配器：基于 epubjs 0.3。构造收 File 或 URL。
// 关键点：
//   1. epubjs 打开失败只 emit 'openFailed'，不会 reject book.ready → 必须用 Promise.race 防挂起
//   2. rendition.display() 是异步的（内部走队列+iframe 加载），必须 await，失败会抛出而非静默
//   3. 进度恢复使用 pendingCfi 暂存机制（store.setAdapter 会在 load 前调 setProgress）
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition } from './types'

export function createEpubAdapter(input: File | string): IBookAdapter {
    let book: any = null
    let rendition: any = null
    let currentCfi = ''
    let pendingCfi: string | null = null
    const metadata: BookMetadata = { title: '', author: '' }

    async function load() {
        const ePub = (await import('epubjs')).default
        const data = typeof input === 'string' ? input : await input.arrayBuffer()
        book = ePub(data)
        // epubjs 打开失败只 emit openFailed，不 reject ready → race 保证不永久挂起
        const fail = new Promise<never>((_, reject) => {
            book.on('openFailed', () => reject(new Error('EPUB 文件损坏或格式不支持')))
        })
        await Promise.race([book.ready, fail])
        const md = await book.loaded.metadata
        metadata.title = md.title || '未知书名'
        metadata.author = md.creator || '未知作者'
    }

    async function getToC(): Promise<ToCItem[]> {
        if (!book) return []
        const nav = await book.loaded.navigation
        // NavItem { id, href, label, subitems? } 与 ToCItem 结构兼容，直接返回
        return nav.toc as ToCItem[]
    }

    async function renderTo(element: HTMLElement) {
        element.innerHTML = ''      // 换书时清掉旧 stage 残留
        rendition = book.renderTo(element, {
            width: '100%',
            height: '100%',
            flow: 'paginated',       // 分页模式
            spread: 'none',          // 单页显示（适配小屏）
            allowScriptedContent: false,   // 安全：禁止 EPUB 内嵌脚本执行
        })
        // 监听翻页事件，更新当前 CFI（epubjs 内部翻页不经过 next/prev）
        rendition.on('relocated', (loc: any) => {
            currentCfi = loc?.start?.cfi ?? ''
        })
        // await：display 失败会抛出（在 ReaderView 显示错误），不再静默吞掉
        await rendition.display(pendingCfi ?? undefined)
        pendingCfi = null
    }

    function getProgress(): ProgressPosition {
        return currentCfi
    }

    async function setProgress(position: ProgressPosition) {
        if (typeof position !== 'string') return
        if (rendition) {
            await rendition.display(position)
        } else {
            pendingCfi = position
        }
    }

    async function next() { await rendition?.next() }
    async function prev() { await rendition?.prev() }

    function getTotal(): number {
        return book?.spine?.length ?? 0    // EPUB 总"页数"动态变化，返回章节数
    }

    function destroy() {
        rendition?.destroy()          // 销毁渲染器（内部 iframe）
        book?.destroy()               // 销毁 book（释放解压缓存）
        rendition = null
        book = null
    }

    return {
        metadata, format: 'epub', load, getToC,
        getProgress, setProgress, renderTo,
        next, prev, getTotal, destroy,
    }
}
