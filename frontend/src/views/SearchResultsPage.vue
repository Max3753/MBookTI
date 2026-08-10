<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchBooks } from '../api'
import { useDebounce } from '../composables/useDebounce'
import type { BookSummary } from '../types/book'
import BookCard from '../components/BookCard.vue'
import { t } from '../composables/useI18n'

const route = useRoute()
const router = useRouter()

const keyword = ref((route.query.q as string) || '')
const books = ref<BookSummary[]>([])
const total = ref(0)
const loading = ref(false)
const searched = ref(false)  // 是否已执行过搜索（区分「首次空态」与「无结果」）

const page = ref(1)
const pageSize = 20
const debouncedKeyword = useDebounce(keyword, 400)

// 关键词防抖后自动搜索（输入即搜）
watch(debouncedKeyword, (val) => {
    const q = val.trim()
    if (!q) {
        books.value = []
        total.value = 0
        searched.value = false
        return
    }
    // 同步 URL query，方便分享/回退
    if (route.query.q !== q) {
        router.replace({ query: { q } })
    }
    page.value = 1
    doSearch(q, 1)
})

async function doSearch(q: string, p: number) {
    loading.value = true
    try {
        const res = await searchBooks(q, p, pageSize)
        books.value = res.data || []
        total.value = res.total || 0
        searched.value = true
    } catch {
        books.value = []
        total.value = 0
        searched.value = true
    } finally {
        loading.value = false
    }
}

// 外部跳转 /search?q=xxx 时响应
watch(
    () => route.query.q,
    (q) => {
        if (typeof q === 'string' && q !== keyword.value) {
            keyword.value = q
        }
    }
)

// 加载更多（简单分页：够用即可，后续量大可换滚动加载）
function loadMore() {
    if (loading.value || books.value.length >= total.value) return
    const next = page.value + 1
    page.value = next
    searchBooks(keyword.value.trim(), next, pageSize)
        .then((res) => {
            books.value = [...books.value, ...(res.data || [])]
            total.value = res.total || 0
        })
        .catch(() => {})
}

onMounted(() => {
    if (keyword.value.trim()) {
        doSearch(keyword.value.trim(), 1)
    }
})
</script>

<template>
  <div>
    <!-- 标题行 -->
    <div class="flex items-center justify-between border-b-2 border-ink dark:border-paper pb-3 mb-6">
      <h2 class="font-serif font-black text-2xl sm:text-3xl tracking-tight">站内书籍搜索</h2>
      <span v-if="searched" class="edition-label text-neutral-400 dark:text-neutral-500">
        共 {{ total }} 条结果
      </span>
    </div>

    <!-- 搜索框 -->
    <div class="max-w-xl mb-8">
      <input
        v-model="keyword"
        type="text"
        placeholder="输入书名 / 作者 / ISBN..."
        class="np-input w-full"
        autofocus
      />
    </div>

    <!-- 首次空态：未搜索时 -->
    <div v-if="!searched && !loading" class="p-12 text-center">
      <p class="font-serif text-2xl text-neutral-400">输入关键词，搜索书库中的书籍</p>
      <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">支持书名、作者模糊匹配，ISBN 精确匹配</p>
    </div>

    <!-- 无结果 -->
    <div v-else-if="searched && books.length === 0 && !loading" class="p-12 text-center">
      <p class="font-serif text-2xl text-neutral-400">未找到与「{{ keyword }}」相关的书籍</p>
      <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">换个关键词试试，或检查 ISBN 是否准确</p>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading && books.length === 0" class="p-12 text-center edition-label text-neutral-400">
      {{ t.loading }}
    </div>

    <!-- 结果网格 -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <BookCard v-for="b in books" :key="b.id" :book="b" show-description />
    </div>

    <!-- 加载更多 -->
    <div v-if="searched && books.length > 0 && books.length < total" class="mt-8 text-center">
      <button
        @click="loadMore"
        :disabled="loading"
        class="np-btn np-btn-ghost px-6 text-sm cursor-pointer"
      >
        {{ loading ? t.loading : '加载更多' }}
      </button>
    </div>
  </div>
</template>
