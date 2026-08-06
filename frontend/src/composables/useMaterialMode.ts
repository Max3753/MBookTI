import { ref, watch } from 'vue'
import { useAuth } from './useAuth'

// 素材模式（Material Mode）：
// 仅管理员可用。开启后移除 newsprint-img 的灰度滤镜，让人格配图/书籍封面恢复全彩，
// 便于管理员截图导出自媒体素材；普通用户永远不启用。状态持久化到 localStorage。
const STORAGE_KEY = 'mbookti_material_mode'

const enabled = ref(localStorage.getItem(STORAGE_KEY) === '1')

function applyToDom(on: boolean) {
    document.documentElement.classList.toggle('material-mode', on)
}

// 同步 DOM class（响应式 watch 保证任何入口切换都一致）
watch(enabled, (v) => applyToDom(v))

export function useMaterialMode() {
    const { user } = useAuth()

    function set(v: boolean) {
        enabled.value = v
        localStorage.setItem(STORAGE_KEY, v ? '1' : '0')
    }

    function toggle() {
        set(!enabled.value)
    }

    // 挂载时由管理员恢复上次状态；非管理员强制关闭
    function init() {
        if (user.value?.is_admin) {
            applyToDom(enabled.value)
        } else {
            enabled.value = false
            localStorage.removeItem(STORAGE_KEY)
            applyToDom(false)
        }
    }

    return { materialMode: enabled, toggle, set, init }
}
