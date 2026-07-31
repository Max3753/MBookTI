// API 配置 — 通过环境变量区分开发/生产
// Vite 环境变量：开发读 .env 文件，生产在构建时注入

const apiConfig = {
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1',
    timeout: 60000,  // AI 生成 + 封面搜索可能耗时较长，放宽到 60 秒
}

export default apiConfig
