<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useTheme } from './composables/useTheme'
import { useAuth } from './composables/useAuth'
import { getUnreadCount } from './api'
import { resolveAssetUrl } from './api/config'
import { t } from './composables/useI18n'

const { isDark, toggle: toggleTheme } = useTheme()
const { user, isLoggedIn, logout, refreshUser } = useAuth()

// 头像加载失败（如旧 URL 已被服务端删除）时回退为首字母墨印
const avatarError = ref(false)
watch(() => user.value?.avatar_url, () => { avatarError.value = false })

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
    // 刷新服务端最新用户信息（头像等可能在其他设备/会话被修改）
    refreshUser()
})

onUnmounted(() => {
    if (unreadTimer !== null) window.clearInterval(unreadTimer)
})

// 报纸头版元数据：今日日期
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
</script>

<template>
  <div class="min-h-screen bg-paper text-ink dark:bg-[#17170f] dark:text-paper">
    <!-- ============ 报纸头版 Masthead ============ -->
    <header class="border-b-4 border-ink dark:border-paper">
      <div class="max-w-screen-xl mx-auto px-4 sm:px-6">
        <!-- 顶部元数据条 -->
        <div class="flex items-center justify-between border-b border-ink/30 dark:border-paper/30 py-1.5 edition-label text-neutral-500 dark:text-neutral-400">
          <span class="hidden sm:inline">VOL. 1 · {{ today }}</span>
          <span class="sm:hidden">VOL. 1</span>
          <span class="text-editorial font-semibold">★ 晨报版 · MORNING EDITION</span>
          <span>{{ isLoggedIn ? '已登录' : '未登录' }}</span>
        </div>

        <!-- 报头标题 -->
        <div class="py-6 text-center">
          <router-link to="/" class="inline-block group">
            <h1 class="font-serif font-black text-5xl sm:text-6xl lg:text-7xl leading-[0.9] tracking-tighter group-hover:text-editorial transition-colors duration-200">
              {{ t.title }}
            </h1>
            <p class="mt-2 font-serif italic text-neutral-500 dark:text-neutral-400 text-sm sm:text-base">{{ t.subtitle }}</p>
          </router-link>
        </div>

        <!-- 导航栏 -->
        <nav class="border-t border-ink/30 dark:border-paper/30">
          <div class="flex items-center justify-between py-2">
            <div class="flex items-center gap-4 sm:gap-6">
              <router-link to="/" class="edition-label text-ink dark:text-paper hover:text-editorial transition-colors duration-200">首页</router-link>
              <router-link v-if="user?.is_admin" to="/admin" class="edition-label text-ink dark:text-paper hover:text-editorial transition-colors duration-200">管理</router-link>
            </div>

            <div class="flex items-center gap-2">
              <!-- 通知铃铛 -->
              <template v-if="isLoggedIn">
                <router-link
                  to="/notifications"
                  class="relative min-h-[44px] min-w-[44px] flex items-center justify-center text-ink dark:text-paper hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors duration-200 cursor-pointer"
                  :title="'通知' + (unread ? `（${unread} 条未读）` : '')"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                  </svg>
                  <span v-if="unread > 0" class="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 bg-editorial text-paper text-[10px] font-bold flex items-center justify-center">
                    {{ unread > 99 ? '99+' : unread }}
                  </span>
                </router-link>
              </template>

              <!-- 用户区 -->
              <template v-if="isLoggedIn">
                <router-link
                  to="/profile"
                  class="flex items-center gap-2 group cursor-pointer min-h-[44px] px-2 max-w-[40vw] sm:max-w-none"
                  :title="`${user?.username} · 个人中心`"
                >
                  <span class="w-8 h-8 shrink-0 text-paper bg-ink dark:bg-paper dark:text-ink flex items-center justify-center text-sm font-bold overflow-hidden">
                    <img v-if="user?.avatar_url && !avatarError" :src="resolveAssetUrl(user.avatar_url)" :alt="user.username" class="w-full h-full object-cover" @error="avatarError = true" />
                    <template v-else>{{ (user?.username || '?')[0].toUpperCase() }}</template>
                  </span>
                  <span class="min-w-0 text-sm font-medium group-hover:text-editorial transition-colors truncate">{{ user?.username }}</span>
                </router-link>
                <button
                  @click="logout"
                  class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs cursor-pointer"
                >
                  退出
                </button>
              </template>
              <template v-else>
                <router-link to="/login" class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs">登录</router-link>
                <router-link to="/register" class="np-btn np-btn-primary !min-h-[36px] px-4 text-xs">注册</router-link>
              </template>

              <!-- 主题切换 -->
              <button @click="toggleTheme" class="np-btn np-btn-ghost !min-h-[36px] px-3 text-xs cursor-pointer">
                {{ isDark ? '☀ 日间' : '☾ 夜间' }}
              </button>
            </div>
          </div>
        </nav>
      </div>
    </header>

    <!-- ============ 主内容区：报纸栏线 ============ -->
    <main class="max-w-screen-xl mx-auto px-4 sm:px-6 py-8">
      <router-view v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </Transition>
      </router-view>
    </main>

    <!-- ============ 页脚：报纸版权线 ============ -->
    <footer class="border-t-4 border-ink dark:border-paper mt-12">
      <div class="max-w-screen-xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 edition-label text-neutral-500 dark:text-neutral-400">
        <span>{{ t.title }} · {{ t.subtitle }}</span>
        <span>EDITION: VOL 1.0 · © {{ new Date().getFullYear() }}</span>
      </div>
    </footer>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
