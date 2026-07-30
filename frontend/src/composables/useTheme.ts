import { ref } from 'vue'

const isDark = ref(localStorage.getItem('theme') === 'dark')

export function useTheme() {
    function sync() {
        document.documentElement.classList.toggle('dark', isDark.value)
        localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
    }

    sync()

    function toggle() {
        isDark.value = !isDark.value
        sync()
    }

    return { isDark, toggle }
}
