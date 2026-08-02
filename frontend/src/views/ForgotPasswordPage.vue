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
    <div class="flex items-center justify-center min-h-[60vh] px-4 py-10">
        <div class="w-full max-w-md">
            <button
                @click="$router.push('/login')"
                class="mb-4 flex items-center gap-1.5 text-sm np-btn-link cursor-pointer"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                </svg>
                返回登录
            </button>
            <div class="np-card p-8 border-b-4 border-editorial animate-newsprint-in">
                <!-- 报头 -->
                <div class="flex items-center justify-between border-b-2 border-ink pb-3 mb-6">
                    <span class="edition-label text-neutral-500 dark:text-neutral-400">MBookTI · 读者服务部</span>
                    <span class="edition-label text-editorial">FORM · 找回栏</span>
                </div>
                <h1 class="font-serif text-3xl font-black text-center tracking-tight mb-8">忘记密码</h1>

                <div v-if="success" class="space-y-6">
                    <!-- 成功提示 -->
                    <div class="border-2 border-ink text-ink dark:text-paper dark:border-paper text-sm px-4 py-3">
                        ✓ 若该邮箱已注册，将收到重置邮件
                    </div>

                    <!-- dev 模式：响应携带 reset_token 时展示开发提示框 -->
                    <div v-if="resetToken" class="border-2 border-ink px-4 py-3 space-y-3 dark:border-paper">
                        <p class="edition-label text-neutral-600 dark:text-neutral-400">
                            【开发模式】当前环境未配置邮件服务，系统返回了重置 token（仅开发环境可见，生产环境不会返回）：
                        </p>
                        <code class="block text-xs font-mono text-ink dark:text-paper border border-ink dark:border-paper px-3 py-2 break-all select-all">{{ resetToken }}</code>
                        <button
                            @click="goReset"
                            class="np-btn np-btn-primary w-full"
                        >
                            下一步
                        </button>
                    </div>
                </div>

                <form v-else @submit.prevent="handleForgot" class="space-y-6">
                    <!-- 错误提示 -->
                    <div v-if="error" class="border-2 border-editorial text-editorial text-sm px-4 py-3">
                        ✗ {{ error }}
                    </div>

                    <!-- 邮箱 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">邮箱</label>
                        <input
                            v-model="email"
                            type="email"
                            placeholder="请输入注册邮箱"
                            class="np-input"
                            autocomplete="email"
                        />
                    </div>

                    <!-- 提交按钮 -->
                    <button
                        type="submit"
                        :disabled="loading"
                        class="np-btn np-btn-primary w-full"
                    >
                        <div v-if="loading" class="w-4 h-4 border-2 border-current border-t-transparent animate-spin"></div>
                        {{ loading ? '发送中...' : '发送重置邮件' }}
                    </button>

                    <!-- 登录链接 -->
                    <p class="text-center text-sm text-neutral-500 dark:text-neutral-400">
                        想起密码了？
                        <router-link to="/login" class="np-btn-link font-medium">返回登录</router-link>
                    </p>
                </form>
            </div>
        </div>
    </div>
</template>
