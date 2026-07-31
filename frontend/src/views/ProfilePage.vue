<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
    getMyProfile,
    updateMyProfile,
    changePassword,
    getMyComments,
    deleteComment,
    getMyFavorites,
} from '../api'
import apiConfig from '../api/config'
import { useAuth } from '../composables/useAuth'
import { getMbtiTypes } from '../api'

const router = useRouter()
const { user, logout } = useAuth()

const profile = ref<any>(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref<'comments' | 'favorites'>('comments')

// 书评
const comments = ref<any[]>([])
const commentsLoading = ref(false)
const deletingId = ref<number | null>(null)

// 收藏
const favorites = ref<any[]>([])
const favoritesLoading = ref(false)

// 编辑资料
const editing = ref(false)
const editUsername = ref('')
const editMbtiId = ref<number | null>(null)
const mbtiTypes = ref<any[]>([])
const saving = ref(false)
const saveMsg = ref('')

// 改密码
const pwOpen = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const pwSubmitting = ref(false)
const pwError = ref('')

// 默认头像色板
const avatarPalette = [
    'bg-indigo-500', 'bg-pink-500', 'bg-emerald-500', 'bg-amber-500',
    'bg-sky-500', 'bg-purple-500', 'bg-rose-500', 'bg-teal-500',
]
const avatarColor = computed(() => {
    const name = profile.value?.username || '?'
    return avatarPalette[name.charCodeAt(0) % avatarPalette.length]
})

// 豆瓣封面代理
function proxyUrl(url: string): string {
    if (!url) return ''
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}

async function loadProfile() {
    try {
        const res = await getMyProfile()
        profile.value = res.data
        editUsername.value = res.data.username
        editMbtiId.value = res.data.mbti_type_id
    } catch (e) {
        error.value = '加载个人资料失败'
    } finally {
        loading.value = false
    }
}

async function loadComments() {
    commentsLoading.value = true
    try {
        const res = await getMyComments()
        comments.value = res.data || []
    } catch {
        comments.value = []
    } finally {
        commentsLoading.value = false
    }
}

async function loadFavorites() {
    favoritesLoading.value = true
    try {
        const res = await getMyFavorites()
        favorites.value = res.data || []
    } catch {
        favorites.value = []
    } finally {
        favoritesLoading.value = false
    }
}

function switchTab(tab: 'comments' | 'favorites') {
    activeTab.value = tab
    if (tab === 'comments' && comments.value.length === 0 && !commentsLoading.value) {
        loadComments()
    }
    if (tab === 'favorites' && favorites.value.length === 0 && !favoritesLoading.value) {
        loadFavorites()
    }
}

async function openEdit() {
    try {
        if (mbtiTypes.value.length === 0) {
            const res = await getMbtiTypes()
            mbtiTypes.value = res.data
        }
    } catch { /* ignore */ }
    editUsername.value = profile.value?.username || ''
    editMbtiId.value = profile.value?.mbti_type_id ?? null
    saveMsg.value = ''
    editing.value = true
}

async function saveProfile() {
    if (!editUsername.value.trim()) return
    saving.value = true
    saveMsg.value = ''
    try {
        const res = await updateMyProfile({
            username: editUsername.value.trim(),
            mbti_type_id: editMbtiId.value,
        })
        profile.value = res.data
        // 同步 localStorage 里的 user（MBTI 联动首页用）
        const cached = JSON.parse(localStorage.getItem('user') || 'null')
        if (cached) {
            cached.username = res.data.username
            cached.mbti_type_id = res.data.mbti_type_id
            localStorage.setItem('user', JSON.stringify(cached))
        }
        editing.value = false
        saveMsg.value = '已保存'
        setTimeout(() => (saveMsg.value = ''), 2000)
    } catch (e: any) {
        saveMsg.value = e.response?.data?.detail || '保存失败'
    } finally {
        saving.value = false
    }
}

function openPw() {
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    pwError.value = ''
    pwOpen.value = true
}

async function submitPassword() {
    if (!oldPassword.value || !newPassword.value) return
    if (newPassword.value !== confirmPassword.value) {
        pwError.value = '两次输入的新密码不一致'
        return
    }
    pwSubmitting.value = true
    pwError.value = ''
    try {
        await changePassword({ old_password: oldPassword.value, new_password: newPassword.value })
        pwOpen.value = false
        // 改密码后强制重新登录
        logout()
        router.push('/login')
    } catch (e: any) {
        pwError.value = e.response?.data?.detail || '修改失败'
    } finally {
        pwSubmitting.value = false
    }
}

async function removeComment(id: number) {
    if (!confirm('确定删除这条书评吗？')) return
    deletingId.value = id
    try {
        await deleteComment(id)
        comments.value = comments.value.filter((c) => c.id !== id)
        if (profile.value) {
            profile.value.stats.comment_count = Math.max(0, profile.value.stats.comment_count - 1)
        }
    } catch {
        alert('删除失败')
    } finally {
        deletingId.value = null
    }
}

onMounted(async () => {
    await loadProfile()
    loadComments()
})
</script>

<template>
    <div>
        <!-- 加载骨架 -->
        <div v-if="loading" class="animate-pulse space-y-6">
            <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div class="flex items-center gap-4">
                    <div class="w-16 h-16 rounded-full bg-gray-200 dark:bg-gray-700"></div>
                    <div class="flex-1 space-y-2">
                        <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
                        <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="error" class="text-center py-20">
            <p class="text-gray-400 mb-3">{{ error }}</p>
            <button @click="location.reload()" class="text-sm text-indigo-600 hover:underline cursor-pointer">重试</button>
        </div>

        <div v-else-if="profile" class="space-y-6">
            <!-- 头部卡片 -->
            <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div class="flex items-start gap-4">
                    <!-- 默认头像 -->
                    <div class="w-16 h-16 rounded-full text-white flex items-center justify-center text-2xl font-bold shrink-0" :class="avatarColor">
                        {{ (profile.username || '?')[0].toUpperCase() }}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100 truncate">{{ profile.username }}</h1>
                            <span v-if="profile.mbti_type_code"
                                class="px-2 py-0.5 text-xs rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-300 shrink-0">
                                {{ profile.mbti_type_code }} {{ profile.mbti_type_name }}
                            </span>
                        </div>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ profile.email }}</p>
                        <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">注册于 {{ new Date(profile.created_at).toLocaleDateString('zh-CN') }}</p>
                    </div>
                    <div class="flex gap-2 shrink-0">
                        <button @click="openEdit"
                            class="px-3 py-1.5 text-xs rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-all duration-200 cursor-pointer">
                            编辑资料
                        </button>
                        <button @click="openPw"
                            class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200 cursor-pointer">
                            改密码
                        </button>
                    </div>
                </div>

                <!-- 统计徽章 -->
                <div class="grid grid-cols-3 gap-3 mt-5">
                    <div class="text-center py-3 rounded-xl bg-gray-50 dark:bg-gray-900/50">
                        <div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ profile.stats.comment_count }}</div>
                        <div class="text-xs text-gray-400 mt-0.5">书评</div>
                    </div>
                    <div class="text-center py-3 rounded-xl bg-gray-50 dark:bg-gray-900/50">
                        <div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ profile.stats.favorite_count }}</div>
                        <div class="text-xs text-gray-400 mt-0.5">收藏</div>
                    </div>
                    <div class="text-center py-3 rounded-xl bg-gray-50 dark:bg-gray-900/50">
                        <div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ profile.stats.like_received }}</div>
                        <div class="text-xs text-gray-400 mt-0.5">获赞</div>
                    </div>
                </div>

                <!-- 编辑资料弹窗 -->
                <div v-if="editing" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="editing = false">
                    <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-sm shadow-xl">
                        <h3 class="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">编辑资料</h3>
                        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">用户名</label>
                        <input v-model="editUsername" type="text"
                            class="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 mb-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">我的 MBTI 类型</label>
                        <select v-model="editMbtiId"
                            class="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 mb-4 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                            <option :value="null">未设置</option>
                            <option v-for="mt in mbtiTypes" :key="mt.id" :value="mt.id">{{ mt.code }} {{ mt.name }}</option>
                        </select>
                        <p v-if="saveMsg" class="text-xs mb-3" :class="saveMsg === '已保存' ? 'text-emerald-500' : 'text-red-500'">{{ saveMsg }}</p>
                        <div class="flex gap-2 justify-end">
                            <button @click="editing = false"
                                class="px-4 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 cursor-pointer">取消</button>
                            <button @click="saveProfile" :disabled="saving"
                                class="px-4 py-2 text-xs rounded-lg bg-indigo-600 text-white disabled:opacity-50 cursor-pointer">
                                {{ saving ? '保存中...' : '保存' }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 改密码弹窗 -->
                <div v-if="pwOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="pwOpen = false">
                    <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-sm shadow-xl">
                        <h3 class="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">修改密码</h3>
                        <input v-model="oldPassword" type="password" placeholder="旧密码"
                            class="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 mb-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                        <input v-model="newPassword" type="password" placeholder="新密码"
                            class="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 mb-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                        <input v-model="confirmPassword" type="password" placeholder="确认新密码"
                            class="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 mb-4 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                        <p v-if="pwError" class="text-xs text-red-500 mb-3">{{ pwError }}</p>
                        <div class="flex gap-2 justify-end">
                            <button @click="pwOpen = false"
                                class="px-4 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 cursor-pointer">取消</button>
                            <button @click="submitPassword" :disabled="pwSubmitting"
                                class="px-4 py-2 text-xs rounded-lg bg-indigo-600 text-white disabled:opacity-50 cursor-pointer">
                                {{ pwSubmitting ? '提交中...' : '确认修改' }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
                <div class="flex border-b border-gray-100 dark:border-gray-700">
                    <button @click="switchTab('comments')"
                        class="flex-1 py-3 text-sm font-medium transition-colors cursor-pointer"
                        :class="activeTab === 'comments'
                            ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                            : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'">
                        我的书评 ({{ profile.stats.comment_count }})
                    </button>
                    <button @click="switchTab('favorites')"
                        class="flex-1 py-3 text-sm font-medium transition-colors cursor-pointer"
                        :class="activeTab === 'favorites'
                            ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                            : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'">
                        我的收藏 ({{ profile.stats.favorite_count }})
                    </button>
                </div>

                <!-- 书评 Tab -->
                <div v-if="activeTab === 'comments'" class="divide-y divide-gray-100 dark:divide-gray-700">
                    <div v-if="commentsLoading" class="p-6 text-center text-gray-400 text-sm">加载中...</div>
                    <div v-else-if="comments.length === 0" class="p-10 text-center text-gray-400 text-sm">
                        还没有书评，去书籍详情页写第一条吧
                    </div>
                    <div v-for="c in comments" :key="c.id" class="p-4 flex gap-3 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition-colors">
                        <router-link :to="`/books/${c.book_id}`" class="w-12 h-16 rounded overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                            <img v-if="c.book_cover_url" :src="proxyUrl(c.book_cover_url)" :alt="c.book_title" class="w-full h-full object-cover" />
                        </router-link>
                        <div class="flex-1 min-w-0">
                            <router-link :to="`/books/${c.book_id}`" class="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline">
                                《{{ c.book_title }}》
                            </router-link>
                            <p class="text-sm text-gray-700 dark:text-gray-300 mt-1 line-clamp-2">{{ c.content }}</p>
                            <p class="text-xs text-gray-400 mt-1.5">
                                {{ new Date(c.created_at).toLocaleString('zh-CN') }} · ♥ {{ c.likes_count }}
                            </p>
                        </div>
                        <button @click="removeComment(c.id)" :disabled="deletingId === c.id"
                            class="text-xs text-red-500 hover:text-red-600 disabled:opacity-50 shrink-0 cursor-pointer">
                            {{ deletingId === c.id ? '删除中...' : '删除' }}
                        </button>
                    </div>
                </div>

                <!-- 收藏 Tab -->
                <div v-else class="p-4">
                    <div v-if="favoritesLoading" class="p-6 text-center text-gray-400 text-sm">加载中...</div>
                    <div v-else-if="favorites.length === 0" class="p-10 text-center text-gray-400 text-sm">
                        还没有收藏的书籍，去详情页点 ♡ 收藏吧
                    </div>
                    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                        <router-link v-for="b in favorites" :key="b.id" :to="`/books/${b.id}`"
                            class="group bg-gray-50 dark:bg-gray-900/50 rounded-xl p-3 hover:shadow-md transition-all duration-200">
                            <div class="w-full h-32 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 mb-2">
                                <img v-if="b.cover_url" :src="proxyUrl(b.cover_url)" :alt="b.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                            </div>
                            <div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{{ b.title }}</div>
                            <div class="text-xs text-gray-400 mt-0.5 truncate">{{ b.author }}</div>
                        </router-link>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
