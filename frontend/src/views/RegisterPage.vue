<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { register } = useAuth()

const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleRegister() {
    if (!username.value || !email.value || !password.value) {
        error.value = '请填写所有字段'
        return
    }
    loading.value = true
    error.value = ''
    try {
        await register(username.value, email.value, password.value)
        router.push('/')
    } catch (e: any) {
        error.value = e.response?.data?.detail || e.message || '注册失败'
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <div class="flex items-center justify-center min-h-[60vh] px-4 py-10">
        <div class="w-full max-w-md">
            <button
                @click="$router.push('/')"
                class="mb-4 flex items-center gap-1.5 text-sm np-btn-link cursor-pointer"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                </svg>
                返回
            </button>
            <div class="np-card p-8 border-b-4 border-editorial animate-newsprint-in">
                <!-- 报头 -->
                <div class="flex items-center justify-between border-b-2 border-ink pb-3 mb-6">
                    <span class="edition-label text-neutral-500 dark:text-neutral-400">MBookTI · 读者服务部</span>
                    <span class="edition-label text-editorial">FORM · 注册栏</span>
                </div>
                <h1 class="font-serif text-3xl font-black text-center tracking-tight mb-8">注册</h1>

                <form @submit.prevent="handleRegister" class="space-y-6">
                    <!-- 错误提示 -->
                    <div v-if="error" class="border-2 border-editorial text-editorial text-sm px-4 py-3">
                        ✗ {{ error }}
                    </div>

                    <!-- 用户名 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">用户名</label>
                        <input
                            v-model="username"
                            type="text"
                            placeholder="请输入用户名"
                            class="np-input"
                            autocomplete="username"
                        />
                    </div>

                    <!-- 邮箱 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">邮箱</label>
                        <input
                            v-model="email"
                            type="email"
                            placeholder="请输入邮箱"
                            class="np-input"
                            autocomplete="email"
                        />
                    </div>

                    <!-- 密码 -->
                    <div>
                        <label class="block font-mono text-xs uppercase tracking-widest text-neutral-600 dark:text-neutral-400 mb-1.5">密码</label>
                        <input
                            v-model="password"
                            type="password"
                            placeholder="请输入密码"
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
                        {{ loading ? '注册中...' : '注册' }}
                    </button>

                    <!-- 登录链接 -->
                    <p class="text-center text-sm text-neutral-500 dark:text-neutral-400">
                        已有账号？
                        <router-link to="/login" class="np-btn-link font-medium">登录</router-link>
                    </p>
                </form>
            </div>
        </div>
    </div>
</template>
