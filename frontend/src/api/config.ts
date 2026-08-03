// API 配置 — 通过环境变量区分开发/生产
// Vite 环境变量：开发读 .env 文件，生产在构建时注入
//
// 开发模式 baseURL 动态化：用当前页面 hostname 拼后端地址。
// 桌面 localhost 访问 → http://localhost:5000/api/v1
// 移动设备经局域网 IP（如 http://192.168.x.x:3000）访问 → http://192.168.x.x:5000/api/v1
// （后端与前端同机，端口固定 5000；生产环境用 VITE_API_BASE_URL 覆盖）

function resolveBaseURL(): string {
    // 显式配置优先（生产构建注入）
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL
    }
    // 开发：跟随当前页面 hostname（支持局域网/移动设备访问）
    const host = window.location.hostname || 'localhost'
    return `http://${host}:5000/api/v1`
}

const apiConfig = {
    baseURL: resolveBaseURL(),
    timeout: 60000,  // AI 生成 + 封面搜索可能耗时较长，放宽到 60 秒
}

// 把后端返回的相对路径（如 /uploads/avatars/xxx.jpg）解析为可访问的完整 URL。
// baseURL 形如 http://host:5000/api/v1（开发）或 /api/v1（生产同源反代），
// 静态文件托管在 origin + /uploads/...（生产经 nginx 反代 /uploads/ 到后端）。
export function resolveAssetUrl(path?: string | null): string {
    if (!path) return ''
    if (/^https?:\/\//.test(path)) return path  // 外部绝对 URL 直接返回
    const origin = apiConfig.baseURL.replace(/\/api\/v1\/?$/, '')
    return `${origin}${path.startsWith('/') ? path : `/${path}`}`
}

export default apiConfig
