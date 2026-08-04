import { createTxtAdapter } from './txtAdapter'
import type { IBookAdapter } from './types'
import { createEpubAdapter } from './epubAdapter'
import { createPdfAdapter } from './pdfAdapter'

/** 按扩展名分发到对应适配器。统一入口：上层无需关心格式。 */
export function createAdapter(file: File): IBookAdapter {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
    switch (ext) {
        case 'txt':
            return createTxtAdapter(file)
        case 'epub':
            return createEpubAdapter(file)   // blob URL 交给适配器
        case 'pdf':
            return createPdfAdapter(file)
        default:
            throw new Error(`暂不支持的文件格式: ${ext || '未知'}`)
    }
}

// 统一重新导出类型，方便上层只从 adapters 导入
export type {
    BookMetadata, ToCItem, BookFormat, ProgressPosition, IBookAdapter,
} from './types'