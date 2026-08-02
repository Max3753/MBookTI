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
                    <span class="edition-label text-editorial">FORM · 重置栏</span>
                </div>
                <h1 class="font-serif text-3xl font-black text-center tracking-tight mb-8">重置密码</h1>

                <form @submit.prevent="handleReset" class="space-y-6">
                    <!-- 错误提示 -->
                    <div v-if="error" class="border-2 border-editorial text-editorial text-sm px-4 py-3">
                        ✗ {{ error }}
                    </div>

                    <!-- 重置 token -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">重置 token</label>
                        <input
                            v-model="token"
                            type="text"
                            placeholder="请输入邮件中的重置 token"
                            class="np-input"
                            autocomplete="off"
                        />
                    </div>

                    <!-- 新密码 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">新密码</label>
                        <input
                            v-model="newPassword"
                            type="password"
                            placeholder="请输入新密码"
                            class="np-input"
                            autocomplete="new-password"
                        />
                    </div>

                    <!-- 确认密码 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">确认密码</label>
                        <input
                            v-model="confirmPassword"
                            type="password"
                            placeholder="请再次输入新密码"
                            class="np-input"
                            autocomplete="new-password"
                        />
                    </div>

                    <!-- 提交按钮 -->
                    <button
                        type="submit"
                        :disabled="loading"
                        class="np-btn np-btn-primary w-full"
                    >
                        <div v-if="loading" class="w-4 h-4 border-2 border-current border-t-transparent animate-spin"></div>
                        {{ loading ? '重置中...' : '重置密码' }}
                    </button>

                    <!-- 登录链接 -->
                    <p class="text-center text-sm text-neutral-500 dark:text-neutral-400">
                        想起来了？
                        <router-link to="/login" class="np-btn-link font-medium">返回登录</router-link>
                    </p>
                </form>
            </div>
        </div>
    </div>
</template>
