// 阅读器本地文件工具：内容哈希（book_key）与 File System Access 句柄持久化
// 设计：文件始终留在本地（不上传），book_key = 文件内容 SHA-256，
// 同一本书（同内容）跨设备/跨浏览器得到相同 key，用于与云端进度记录关联。

const HANDLES_DB = 'mbookti_reader_handles'
const HANDLES_STORE = 'handles'

// ---- 纯 JS SHA-256（不依赖 crypto.subtle）----
// crypto.subtle 仅在安全上下文（HTTPS/localhost）可用；生产环境 http://IP 访问时
// crypto.subtle 为 undefined，需用纯 JS 实现兜底，保证任意环境下 book_key 可计算。

const SHA256_K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])

const SHA256_H0 = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
])

function rotr(x: number, n: number): number {
    return (x >>> n) | (x << (32 - n))
}

/** 纯 JS SHA-256，输入字节数组，输出 64 位小写十六进制 */
function sha256HexBytes(data: Uint8Array): string {
    const bitLenHi = Math.floor(data.length / 0x20000000)   // 字节数 * 8 的高 32 位
    const bitLenLo = (data.length << 3) >>> 0                // 低 32 位
    // 填充：0x80 + 零 + 8 字节大端长度（共 64 字节对齐）
    const padLen = ((data.length + 8) >> 6 << 6) + 64
    const msg = new Uint8Array(padLen)
    msg.set(data)
    msg[data.length] = 0x80
    const view = new DataView(msg.buffer)
    view.setUint32(padLen - 8, bitLenHi, false)
    view.setUint32(padLen - 4, bitLenLo, false)

    const w = new Uint32Array(64)
    const h = SHA256_H0.slice()

    for (let off = 0; off < padLen; off += 64) {
        for (let t = 0; t < 16; t++) w[t] = view.getUint32(off + t * 4, false)
        for (let t = 16; t < 64; t++) {
            const s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3)
            const s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10)
            w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0
        }
        let a = h[0], b = h[1], c = h[2], d = h[3]
        let e = h[4], f = h[5], g = h[6], hh = h[7]
        for (let t = 0; t < 64; t++) {
            const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
            const ch = (e & f) ^ (~e & g)
            const t1 = (hh + S1 + ch + SHA256_K[t] + w[t]) >>> 0
            const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
            const maj = (a & b) ^ (a & c) ^ (b & c)
            const t2 = (S0 + maj) >>> 0
            hh = g; g = f; f = e
            e = (d + t1) >>> 0
            d = c; c = b; b = a
            a = (t1 + t2) >>> 0
        }
        h[0] = (h[0] + a) >>> 0; h[1] = (h[1] + b) >>> 0
        h[2] = (h[2] + c) >>> 0; h[3] = (h[3] + d) >>> 0
        h[4] = (h[4] + e) >>> 0; h[5] = (h[5] + f) >>> 0
        h[6] = (h[6] + g) >>> 0; h[7] = (h[7] + hh) >>> 0
    }

    let out = ''
    for (let i = 0; i < 8; i++) {
        out += h[i].toString(16).padStart(8, '0')
    }
    return out
}

/** 计算文件内容 SHA-256（64 位十六进制）作为稳定 book_key。
 *  优先原生 crypto.subtle（快）；非安全上下文（http://IP）自动降级纯 JS 实现。 */
export async function hashFile(file: File | Blob): Promise<string> {
    const buf = new Uint8Array(await file.arrayBuffer())
    if (typeof crypto !== 'undefined' && crypto.subtle?.digest) {
        const digest = await crypto.subtle.digest('SHA-256', buf)
        return Array.from(new Uint8Array(digest))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('')
    }
    return sha256HexBytes(buf)
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
