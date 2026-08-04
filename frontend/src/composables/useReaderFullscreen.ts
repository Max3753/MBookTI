import { onBeforeUnmount, onMounted, shallowRef } from 'vue'
import type { Ref } from 'vue'

// 覆盖旧 WebKit/Blink/Firefox 的前缀事件（VueUse useFullscreen 同款集合）
const FS_EVENTS = [
    'fullscreenchange',
    'webkitfullscreenchange',
    'webkitendfullscreen',
    'mozfullscreenchange',
    'MSFullscreenChange',
]

type FSElement = HTMLElement & {
    webkitRequestFullscreen?: () => void
    mozRequestFullScreen?: () => void
    msRequestFullscreen?: () => void
}
type FSDocument = Document & {
    webkitExitFullscreen?: () => void
    mozCancelFullScreen?: () => void
    msExitFullscreen?: () => void
    webkitFullscreenElement?: Element | null
    mozFullScreenElement?: Element | null
    msFullscreenElement?: Element | null
}

/**
 * 阅读器全屏切换：
 * - 全屏目标 = 传入的元素（建议用「容器 + 操作条」的外层，全屏后仍可翻页/退出）
 * - 监听 fullscreenchange（用户按 Esc/F11 退出也能同步图标状态）
 * - 组件卸载时自动退出全屏（路由离开）
 */
export function useReaderFullscreen(target: Ref<HTMLElement | null>) {
    const isFullscreen = shallowRef(false)
    const isSupported = typeof document !== 'undefined'
        && 'fullscreenEnabled' in document
        && document.fullscreenEnabled

    function enter() {
        const el = target.value as FSElement | null
        if (!el) return
        if (el.requestFullscreen) {
            void el.requestFullscreen()
        } else if (el.webkitRequestFullscreen) {
            el.webkitRequestFullscreen()
        } else if (el.mozRequestFullScreen) {
            el.mozRequestFullScreen()
        } else if (el.msRequestFullscreen) {
            el.msRequestFullscreen()
        }
    }

    function exit() {
        const d = document as FSDocument
        if (d.exitFullscreen) {
            void d.exitFullscreen()
        } else if (d.webkitExitFullscreen) {
            d.webkitExitFullscreen()
        } else if (d.mozCancelFullScreen) {
            d.mozCancelFullScreen()
        } else if (d.msExitFullscreen) {
            d.msExitFullscreen()
        }
    }

    async function toggle() {
        const d = document as FSDocument
        const active = d.fullscreenElement ?? d.webkitFullscreenElement
            ?? d.mozFullScreenElement ?? d.msFullscreenElement
        if (active) {
            await exit()
        } else {
            enter()
        }
    }

    function onChange() {
        const d = document as FSDocument
        const active = d.fullscreenElement ?? d.webkitFullscreenElement
            ?? d.mozFullScreenElement ?? d.msFullscreenElement
        isFullscreen.value = Boolean(active) && active === target.value
    }

    onMounted(() => {
        for (const ev of FS_EVENTS) document.addEventListener(ev, onChange)
        onChange()
    })

    onBeforeUnmount(() => {
        exit()
        for (const ev of FS_EVENTS) document.removeEventListener(ev, onChange)
    })

    return { isFullscreen, isSupported, toggle }
}
