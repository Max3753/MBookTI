<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { forgotPassword } from '../api'

const router = useRouter()

const email = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)
const resetToken = ref('')

async function handleForgot() {
    if (!email.value.trim()) {
        error.value = '请输入邮箱'
        return
    }
    loading.value = true
    error.value = ''
    try {
        const res = await forgotPassword(email.value.trim())
        // 统一响应格式 {data, message}：生产模式 data 为 null，dev 模式 data.reset_token 携带重置 token
        const token = (res as any)?.data?.reset_token
        resetToken.value = typeof token === 'string' && token ? token : ''
        success.value = true
    } catch (e: any) {
        error.value = e.response?.data?.detail || e.message || '发送失败'
    } finally {
        loading.value = false
    }
}

function goReset() {
    router.push(`/reset-password?token=${encodeURIComponent(resetToken.value)}`)
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
            <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6 text-center">忘记密码</h1>

            <div v-if="success" class="space-y-5">
                <!-- 成功提示 -->
                <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-600 dark:text-green-400 text-sm rounded-lg px-4 py-3">
                    若该邮箱已注册，将收到重置邮件
                </div>

                <!-- dev 模式：响应携带 reset_token 时展示开发提示框 -->
                <div v-if="resetToken" class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg px-4 py-3 space-y-3">
                    <p class="text-xs text-yellow-700 dark:text-yellow-400">
                        【开发模式】当前环境未配置邮件服务，系统返回了重置 token（仅开发环境可见，生产环境不会返回）：
                    </p>
                    <code class="block text-xs text-yellow-800 dark:text-yellow-300 bg-white dark:bg-gray-800 border border-yellow-200 dark:border-yellow-800 rounded px-3 py-2 break-all select-all">{{ resetToken }}</code>
                    <button
                        @click="goReset"
                        class="w-full bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-lg px-6 py-2.5 font-medium transition-all duration-200 cursor-pointer"
                    >
                        下一步
                    </button>
                </div>
            </div>

            <form v-else @submit.prevent="handleForgot" class="space-y-5">
                <!-- 错误提示 -->
                <div v-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm rounded-lg px-4 py-3">
                    {{ error }}
                </div>

                <!-- 邮箱 -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">邮箱</label>
                    <input
                        v-model="email"
                        type="email"
                        placeholder="请输入注册邮箱"
                        class="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all duration-200"
                        autocomplete="email"
                    />
                </div>

                <!-- 提交按钮 -->
                <button
                    type="submit"
                    :disabled="loading"
                    class="w-full bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-lg px-6 py-2.5 font-medium transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    <div v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {{ loading ? '发送中...' : '发送重置邮件' }}
                </button>

                <!-- 登录链接 -->
                <p class="text-center text-sm text-gray-500 dark:text-gray-400">
                    想起密码了？
                    <router-link to="/login" class="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">返回登录</router-link>
                </p>
            </form>
        </div>
        </div>
    </div>
</template>
