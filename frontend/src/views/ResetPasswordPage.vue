<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resetPassword } from '../api'

const route = useRoute()
const router = useRouter()

// 从 query 自动读取 token 预填（可修改）
const token = ref((typeof route.query.token === 'string' ? route.query.token : '') || '')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

async function handleReset() {
    if (!token.value.trim()) {
        error.value = '缺少重置 token'
        return
    }
    if (!newPassword.value || !confirmPassword.value) {
        error.value = '请填写所有字段'
        return
    }
    if (newPassword.value !== confirmPassword.value) {
        error.value = '两次输入的密码不一致'
        return
    }
    loading.value = true
    error.value = ''
    try {
        await resetPassword(token.value.trim(), newPassword.value)
        router.push('/login?success=1')
    } catch (e: any) {
        error.value = e.response?.data?.detail || e.message || '重置失败'
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <div class="flex items-center justify-center min-h-[60vh]">
        <div class="w-full max-w-md">
          <button
            @click="$router.push('/login')"
            class="mb-3 flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors duration-200 cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            返回登录
          </button>
          <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-8">
            <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6 text-center">重置密码</h1>

            <form @submit.prevent="handleReset" class="space-y-5">
                <!-- 错误提示 -->
                <div v-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm rounded-lg px-4 py-3">
                    {{ error }}
                </div>

                <!-- 重置 token -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">重置 token</label>
                    <input
                        v-model="token"
                        type="text"
                        placeholder="请输入邮件中的重置 token"
                        class="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all duration-200"
                        autocomplete="off"
                    />
                </div>

                <!-- 新密码 -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">新密码</label>
                    <input
                        v-model="newPassword"
                        type="password"
                        placeholder="请输入新密码"
                        class="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all duration-200"
                        autocomplete="new-password"
                    />
                </div>

                <!-- 确认密码 -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">确认密码</label>
                    <input
                        v-model="confirmPassword"
                        type="password"
                        placeholder="请再次输入新密码"
                        class="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all duration-200"
                        autocomplete="new-password"
                    />
                </div>

                <!-- 提交按钮 -->
                <button
                    type="submit"
                    :disabled="loading"
                    class="w-full bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-lg px-6 py-2.5 font-medium transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    <div v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {{ loading ? '重置中...' : '重置密码' }}
                </button>

                <!-- 登录链接 -->
                <p class="text-center text-sm text-gray-500 dark:text-gray-400">
                    想起来了？
                    <router-link to="/login" class="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">返回登录</router-link>
                </p>
            </form>
        </div>
        </div>
    </div>
</template>
