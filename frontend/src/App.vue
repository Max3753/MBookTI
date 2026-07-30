<script setup lang="ts">
import { useTheme } from './composables/useTheme'
import { t } from './composables/useI18n'

const { isDark, toggle: toggleTheme } = useTheme()
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
    <header class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-100 dark:border-gray-700">
      <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <div>
          <router-link to="/" class="text-xl font-bold text-indigo-600 dark:text-indigo-400">
            {{ t.title }}
          </router-link>
          <span class="ml-2 text-sm text-gray-400 dark:text-gray-500">{{ t.subtitle }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button @click="toggleTheme" class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition cursor-pointer">
            {{ isDark ? '☀️' : '🌙' }}
          </button>
        </div>
      </div>
    </header>
    <main class="max-w-4xl mx-auto px-4 py-6">
      <router-view/>
    </main>
  </div>
</template>