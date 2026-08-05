// EPUB 适配器：基于 epubjs 0.3。构造收 File 或 URL。
// 关键点：
//   1. epubjs 打开失败只 emit 'openFailed'，不会 reject book.ready → 必须用 Promise.race 防挂起
//   2. rendition.display() 是异步的（内部走队列+iframe 加载），必须 await，失败会抛出而非静默
//   3. 进度恢复使用 pendingCfi 暂存机制（store.setAdapter 会在 load 前调 setProgress）
import type { IBookAdapter, BookMetadata, ToCItem, ProgressPosition, ReaderTypography } from './types'

// 字体栈：与 ReaderView 的 CSS 变量保持一致（TXT/EPUB 共用同一套字体偏好）
const FONT_STACKS: Record<NonNullable<ReaderTypography['fontFamily']>, string | null> = {
    default: null,   // 不注入，保留 EPUB 自身排版
    serif: "'Songti SC', 'SimSun', 'Noto Serif CJK SC', Georgia, 'Times New Roman', serif",
    sans: "'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Helvetica Neue', Arial, sans-serif",
}

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
            progressListener?.()
        })

        // spine 为空（OPF 解析异常/损坏）：提前给友好错误，避免落到难懂的 "No Section Found"
        if (!book.spine?.length) {
            throw new Error('EPUB 文件损坏：未解析到任何章节')
        }

        // 进度 CFI 预校验：spine.get 对 CFI 用 spinePos 索引章节，
        // 进度来自旧版本/内容变化/畸形 CFI 时可能匹配不到 → 降级从第一章开始，不阻塞打开
        let target: string | undefined
        if (pendingCfi) {
            try {
                if (book.spine.get(pendingCfi)) target = pendingCfi
            } catch {
                target = undefined   // 畸形 CFI 也不阻塞打开
            }
        }

        try {
            // await：display 失败会抛出（在 ReaderView 显示错误），不再静默吞掉
            await rendition.display(target)
        } catch (e) {
            // 兜底：带 CFI 显示失败（epubjs 解析边缘情况）→ 去掉进度重试第一章
            if (target) {
                await rendition.display()
            } else {
                throw e
            }
        }
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

    // 应用背景/文字色 + 排版：注入 body 级 !important 规则压过内容自带样式。
    // 不能用 themes.override —— 它只设 documentElement，EPUB 内容 body 的自带背景会盖住它。
    // 用 register(rules) + select：换章节时 epubjs 的 inject 钩子会对 rules 主题自动重新注入；
    // 换色时同 key 覆盖，register 内部对已注入主题执行 update 替换。
    function setTheme(bgColor: string, fgColor: string, typo?: ReaderTypography) {
        const themes = rendition?.themes
        if (!themes) return
        const rules: Record<string, Record<string, string>> = {
            body: {
                'background-color': `${bgColor} !important`,
                'color': `${fgColor} !important`,
            },
        }
        if (typo) {
            const fontStack = FONT_STACKS[typo.fontFamily]
            rules.body['line-height'] = `${typo.lineHeight} !important`
            if (fontStack) rules.body['font-family'] = `${fontStack} !important`
            // 首行缩进作用于正文段落：EPUB 内容 p 可能自带缩进，用 !important 统一
            rules['p'] = { 'text-indent': typo.indent ? '2em !important' : '0 !important' }
        }
        themes.register('reader-custom-theme', rules)
        themes.select('reader-custom-theme')
    }

    // 内部翻页（epubjs 滑动/链接跳转）时通知阅读器刷新进度文案
    let progressListener: (() => void) | null = null
    function onProgressChange(listener: () => void) {
        progressListener = listener
    }

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
        next, prev, setTheme, onProgressChange, getTotal, destroy,
    }
}
