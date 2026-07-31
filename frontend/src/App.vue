<script setup lang="ts">
import { useTheme } from './composables/useTheme'
import { useAuth } from './composables/useAuth'
import { t } from './composables/useI18n'

const { isDark, toggle: toggleTheme } = useTheme()
const { user, isLoggedIn, logout } = useAuth()
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
          <!-- Auth buttons -->
          <template v-if="isLoggedIn">
            <span class="text-sm text-gray-600 dark:text-gray-300">{{ user?.username }}</span>
            <button
              @click="logout"
              class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200 cursor-pointer"
            >
              退出
            </button>
          </template>
          <template v-else>
            <router-link
              to="/login"
              class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200 cursor-pointer"
            >
              登录
            </router-link>
            <router-link
              to="/register"
              class="px-3 py-1.5 text-xs rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white transition-all duration-200 cursor-pointer"
            >
              注册
            </router-link>
          </template>
          <!-- Theme toggle -->
          <button @click="toggleTheme" class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200 cursor-pointer">
            {{ isDark ? '☀️' : '🌙' }}
          </button>
        </div>
      </div>
    </header>
    <main class="max-w-4xl mx-auto px-4 py-6">
      <router-view v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
