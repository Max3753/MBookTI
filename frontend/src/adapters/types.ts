// 统一适配器接口：EPUB/PDF/TXT 三种格式都实现此接口，
// 阅读器组件只依赖这里的抽象，不关心具体格式内部。

export interface BookMetadata {
    title: string;
    author: string;
}

export interface ToCItem {
    id: string;
    label: string;
    href?: string;
    subitems?: ToCItem[]
}

export type BookFormat = 'epub' | 'pdf' | 'txt'

// 进度位置：EPUB 存 CFI 字符串；PDF 存页码；TXT 存段落索引数字
export type ProgressPosition = string | number

export interface IBookAdapter {
    readonly metadata: BookMetadata
    readonly format: BookFormat

    /** 异步加载并解析文件（epubjs/pdfjs 在此刻才动态 import） */
    load(): Promise<void>

    /** 返回目录树 */
    getToC(): Promise<ToCItem[]>

    /** 返回当前进度（EPUB=CFI / PDF=页码 / TXT=段落索引） */
    getProgress(): ProgressPosition

    /** 总章节/页/段落数（UI 显示用；EPUB=章节数，PDF=页数，TXT=段落数） */
    getTotal(): number

    /** 跳到指定进度 */
    setProgress(position: ProgressPosition): void | Promise<void>

    /** 渲染到容器元素（EPUB→内部 iframe / PDF→canvas / TXT→DOM） */
    renderTo(element: HTMLElement): void | Promise<void>

    next(): void | Promise<void>
    prev(): void | Promise<void>

    /**
     * 容器尺寸变化后重排（可选；全屏/窗口 resize 时由阅读器调用）。
     * TXT 重算分页并保持当前进度；EPUB/PDF 依赖自身响应式布局可省略。
     */
    relayout?(): void | Promise<void>

    /** 释放资源（销毁 rendition、撤销 ObjectURL 等）*/
    destroy(): void
}
