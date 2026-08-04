// 阅读器本地文件工具：内容哈希（book_key）与 File System Access 句柄持久化
// 设计：文件始终留在本地（不上传），book_key = 文件内容 SHA-256，
// 同一本书（同内容）跨设备/跨浏览器得到相同 key，用于与云端进度记录关联。

const HANDLES_DB = 'mbookti_reader_handles'
const HANDLES_STORE = 'handles'

/** 计算文件内容 SHA-256（64 位十六进制）作为稳定 book_key */
export async function hashFile(file: File | Blob): Promise<string> {
    const buf = await file.arrayBuffer()
    const digest = await crypto.subtle.digest('SHA-256', buf)
    return Array.from(new Uint8Array(digest))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
}

/** 是否支持 File System Access API（Chromium 系 + 安全上下文 localhost/https） */
export function isFileSystemAccessSupported(): boolean {
    return typeof window !== 'undefined' && 'showOpenFilePicker' in window
}

export interface PickedBook {
    file: File
    bookKey: string
    handle?: FileSystemFileHandle
}

/** 打开系统文件选择器。优先 File System Access API（返回可持久化句柄）；取消返回 null */
export async function pickLocalBook(): Promise<PickedBook | null> {
    const w = window as unknown as {
        showOpenFilePicker?: (opts: unknown) => Promise<FileSystemFileHandle[]>
    }
    if (typeof w.showOpenFilePicker === 'function') {
        try {
            const [handle] = await w.showOpenFilePicker({
                types: [{
                    description: '电子书',
                    accept: {
                        'application/octet-stream': ['.txt', '.epub', '.pdf'],
                        'text/plain': ['.txt'],
                        'application/pdf': ['.pdf'],
                        'application/epub+zip': ['.epub'],
                    },
                }],
                multiple: false,
            })
            const file = await handle.getFile()
            const bookKey = await hashFile(file)
            return { file, bookKey, handle }
        } catch (e) {
            if (e instanceof DOMException && e.name === 'AbortError') return null  // 用户取消
            throw e
        }
    }
    return null  // 不支持 FS Access API → 调用方回退 input
}

// ---- 文件句柄持久化（IndexedDB）----
// 句柄可在页面重开后复用：同一设备免重复选文件，直接续读
// （Chromium 需用户授予读权限，见 ensureReadPermission）

function openHandlesDb(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(HANDLES_DB, 1)
        req.onupgradeneeded = () => {
            req.result.createObjectStore(HANDLES_STORE)   // keyPath: book_key
        }
        req.onsuccess = () => resolve(req.result)
        req.onerror = () => reject(req.error)
    })
}

export async function saveFileHandle(bookKey: string, handle: FileSystemFileHandle): Promise<void> {
    try {
        const db = await openHandlesDb()
        await new Promise<void>((resolve, reject) => {
            const tx = db.transaction(HANDLES_STORE, 'readwrite')
            tx.objectStore(HANDLES_STORE).put(handle, bookKey)
            tx.oncomplete = () => resolve()
            tx.onerror = () => reject(tx.error)
        })
        db.close()
    } catch { /* 句柄保存失败不阻塞阅读 */ }
}

export async function getFileHandle(bookKey: string): Promise<FileSystemFileHandle | null> {
    try {
        const db = await openHandlesDb()
        const handle = await new Promise<FileSystemFileHandle | undefined>((resolve, reject) => {
            const tx = db.transaction(HANDLES_STORE, 'readonly')
            const req = tx.objectStore(HANDLES_STORE).get(bookKey)
            req.onsuccess = () => resolve(req.result)
            req.onerror = () => reject(req.error)
        })
        db.close()
        return handle ?? null
    } catch {
        return null
    }
}

export async function deleteFileHandle(bookKey: string): Promise<void> {
    try {
        const db = await openHandlesDb()
        await new Promise<void>((resolve, reject) => {
            const tx = db.transaction(HANDLES_STORE, 'readwrite')
            tx.objectStore(HANDLES_STORE).delete(bookKey)
            tx.oncomplete = () => resolve()
            tx.onerror = () => reject(tx.error)
        })
        db.close()
    } catch { /* 静默 */ }
}

/** 确保句柄可读（请求用户授权，返回是否可读） */
export async function ensureReadPermission(handle: FileSystemFileHandle): Promise<boolean> {
    try {
        const opts = { mode: 'read' as const }
        const h = handle as FileSystemFileHandle & {
            queryPermission?: (opts: { mode: 'read' }) => Promise<PermissionState>
            requestPermission?: (opts: { mode: 'read' }) => Promise<PermissionState>
        }
        if (h.queryPermission && (await h.queryPermission(opts)) === 'granted') return true
        if (h.requestPermission && (await h.requestPermission(opts)) === 'granted') return true
        return false
    } catch {
        return false
    }
}

/** 通过持久化句柄重新取文件（无感续读路径）；不可读/失败返回 null */
export async function getFileFromHandle(handle: FileSystemFileHandle): Promise<File | null> {
    try {
        if (!(await ensureReadPermission(handle))) return null
        return await handle.getFile()
    } catch {
        return null
    }
}
