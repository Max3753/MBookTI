<script setup lang="ts">
import apiConfig from '../api/config'
import type { BookSummary } from '../types/book'

const props = defineProps<{
    book: BookSummary
    showDescription?: boolean
}>()

// 豆瓣图床防盗链：与详情页/收藏页一致，封面一律走后端代理
function proxyUrl(url: string): string {
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}
</script>

<template>
  <router-link :to="`/books/${book.id}`" class="np-card np-card-hover p-3 block group">
    <div class="w-full h-32 border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800 mb-2">
      <img v-if="book.cover_url" :src="proxyUrl(book.cover_url)" :alt="book.title"
        class="w-full h-full object-cover newsprint-img" />
      <div v-else class="w-full h-full halftone flex items-center justify-center">
        <span class="font-serif text-3xl text-neutral-400">{{ book.title[0] || '书' }}</span>
      </div>
    </div>
    <div class="flex items-start justify-between gap-1">
      <div class="min-w-0">
        <div class="text-sm font-medium font-serif truncate text-ink dark:text-paper group-hover:text-editorial transition-colors duration-200">
          {{ book.title }}
        </div>
        <div class="edition-label text-neutral-400 dark:text-neutral-500 mt-0.5 truncate">{{ book.author }}</div>
      </div>
      <span v-if="book.genre" class="np-badge np-badge-outline leading-none shrink-0 mt-0.5">{{ book.genre }}</span>
    </div>
    <p v-if="showDescription && book.description" class="mt-2 text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 font-body">
      {{ book.description }}
    </p>
  </router-link>
</template>
