// 防抖工具：延迟执行传入函数，用于搜索输入等高频触发场景
import { ref, watch, type Ref } from 'vue'

export function useDebounce<T>(value: Ref<T>, delay = 300) {
    const debounced = ref(value.value) as Ref<T>
    let timer: number | null = null

    watch(value, (val) => {
        if (timer !== null) window.clearTimeout(timer)
        timer = window.setTimeout(() => {
            debounced.value = val
        }, delay)
    })

    return debounced
}
