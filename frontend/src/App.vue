<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from './composables/useTheme'
import { useAuth } from './composables/useAuth'
import { getUnreadCount } from './api'
import { t } from './composables/useI18n'

const { isDark, toggle: toggleTheme } = useTheme()
const { user, isLoggedIn, logout } = useAuth()

// 通知未读数（铃铛红点，轻量轮询）
const unread = ref(0)
let unreadTimer: number | null = null

async function refreshUnread() {
    if (!isLoggedIn.value) {
        unread.value = 0
        return
    }
    try {
        const res = await getUnreadCount()
        unread.value = res.data?.unread || 0
    } catch { /* 忽略 */ }
}

onMounted(() => {
    refreshUnread()
    unreadTimer = window.setInterval(refreshUnread, 30000)
})

onUnmounted(() => {
    if (unreadTimer !== null) window.clearInterval(unreadTimer)
})
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
            <router-link
              to="/notifications"
              class="relative p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200 cursor-pointer"
              :title="'通知' + (unread ? `（${unread} 条未读）` : '')"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
              <span v-if="unread > 0" class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                {{ unread > 99 ? '99+' : unread }}
              </span>
            </router-link>
            <router-link
              v-if="user?.is_admin"
              to="/admin"
              class="relative p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200 cursor-pointer"
              title="管理后台"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </router-link>
            <router-link
              to="/profile"
              class="flex items-center gap-2 group cursor-pointer"
              :title="`${user?.username} · 个人中心`"
            >
              <span
                class="w-8 h-8 rounded-full text-white flex items-center justify-center text-sm font-bold bg-indigo-500 group-hover:ring-2 group-hover:ring-indigo-300 transition-all duration-200"
              >
                {{ (user?.username || '?')[0].toUpperCase() }}
              </span>
              <span class="text-sm text-gray-600 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                {{ user?.username }}
              </span>
            </router-link>
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
