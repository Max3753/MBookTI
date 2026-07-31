<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import {
    publishAnnouncement,
    getAnnouncementList,
    deactivateAnnouncement,
    getUsers,
    sendAdminMessage,
    adminResetPassword,
} from '../api'

const router = useRouter()
const { user } = useAuth()

// 非管理员直接踢回首页（双保险：路由守卫 + 组件内校验）
if (!user.value?.is_admin) {
    router.replace('/')
}

// ---------- 公告管理 ----------
const activeTab = ref<'announcements' | 'messages'>('announcements')
const annTitle = ref('')
const annContent = ref('')
const announcements = ref<any[]>([])
const annLoading = ref(false)
const publishing = ref(false)
const annTotal = ref(0)

async function loadAnnouncements() {
    annLoading.value = true
    try {
        const res = await getAnnouncementList(1, 50)
        announcements.value = res.data || []
        annTotal.value = res.total || 0
    } catch {
        announcements.value = []
    } finally {
        annLoading.value = false
    }
}

async function publish() {
    if (!annTitle.value.trim() || !annContent.value.trim()) return
    publishing.value = true
    try {
        await publishAnnouncement({ title: annTitle.value.trim(), content: annContent.value.trim() })
        annTitle.value = ''
        annContent.value = ''
        await loadAnnouncements()
    } finally {
        publishing.value = false
    }
}

async function deactivate(id: number) {
    if (!confirm('确定下线这条公告？下线后所有用户将不再看到')) return
    try {
        await deactivateAnnouncement(id)
        await loadAnnouncements()
    } catch { /* 忽略 */ }
}

// ---------- 用户消息 ----------
const users = ref<any[]>([])
const usersLoading = ref(false)
const userTotal = ref(0)
const searchText = ref('')
const selectedUserId = ref<number | null>(null)
const msgContent = ref('')
const sending = ref(false)

const filteredUsers = computed(() => {
    const kw = searchText.value.trim().toLowerCase()
    if (!kw) return users.value
    return users.value.filter((u) =>
        String(u.username).toLowerCase().includes(kw) || String(u.id) === kw
    )
})

async function loadUsers() {
    usersLoading.value = true
    try {
        const res = await getUsers(1, 50)
        users.value = res.data || []
        userTotal.value = res.total || 0
    } catch {
        users.value = []
    } finally {
        usersLoading.value = false
    }
}

function selectUser(id: number) {
    selectedUserId.value = selectedUserId.value === id ? null : id
}

async function sendMessage() {
    if (selectedUserId.value === null || !msgContent.value.trim()) return
    sending.value = true
    try {
        await sendAdminMessage(selectedUserId.value, msgContent.value.trim())
        msgContent.value = ''
        selectedUserId.value = null
    } finally {
        sending.value = false
    }
}

// ---------- 重置用户密码 ----------
const newPwd = ref('')
const resetting = ref(false)
const resetSuccess = ref('')
const resetError = ref('')

async function handleResetPassword() {
    if (selectedUserId.value === null || !newPwd.value.trim()) return
    resetting.value = true
    resetSuccess.value = ''
    resetError.value = ''
    try {
        await adminResetPassword(selectedUserId.value, newPwd.value.trim())
        newPwd.value = ''
        resetSuccess.value = `已重置 #${selectedUserId.value} 的密码`
    } catch (e: any) {
        resetError.value = e.response?.data?.detail || e.message || '重置失败'
    } finally {
        resetting.value = false
    }
}

function formatTime(dateStr: string): string {
    const d = new Date(dateStr)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => {
    loadAnnouncements()
    loadUsers()
})
</script>

<template>
    <div>
        <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">管理后台</h1>

        <!-- Tab 切换 -->
        <div class="flex gap-2 mb-6">
            <button
                @click="activeTab = 'announcements'"
                class="px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer"
                :class="activeTab === 'announcements'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'"
            >
                公告管理
            </button>
            <button
                @click="activeTab = 'messages'"
                class="px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer"
                :class="activeTab === 'messages'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'"
            >
                用户消息
            </button>
        </div>

        <!-- ============ 公告管理 ============ -->
        <section v-if="activeTab === 'announcements'" class="space-y-6">
            <!-- 发布表单 -->
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-5">
                <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">发布系统公告</h2>
                <input
                    v-model="annTitle"
                    type="text"
                    placeholder="公告标题（1-100 字）"
                    maxlength="100"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-3"
                />
                <textarea
                    v-model="annContent"
                    placeholder="公告内容（1-5000 字）"
                    maxlength="5000"
                    rows="4"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y mb-3"
                ></textarea>
                <div class="flex items-center justify-between">
                    <span class="text-xs text-gray-400">{{ annContent.length }}/5000</span>
                    <button
                        @click="publish"
                        :disabled="publishing || !annTitle.trim() || !annContent.trim()"
                        class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    >
                        {{ publishing ? '发布中...' : '发布公告' }}
                    </button>
                </div>
            </div>

            <!-- 已发布列表 -->
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">已发布公告（{{ annTotal }}）</h2>
                </div>
                <div v-if="annLoading" class="p-8 text-center text-gray-400 text-sm">加载中...</div>
                <div v-else-if="announcements.length === 0" class="p-8 text-center text-gray-400 text-sm">暂无公告</div>
                <div v-else class="divide-y divide-gray-100 dark:divide-gray-700">
                    <div v-for="a in announcements" :key="a.id" class="px-5 py-4 flex items-start gap-3">
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2">
                                <span class="text-sm font-medium text-gray-800 dark:text-gray-100">{{ a.title }}</span>
                                <span
                                    class="text-xs px-1.5 py-0.5 rounded shrink-0"
                                    :class="a.is_active
                                        ? 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400'
                                        : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'"
                                >
                                    {{ a.is_active ? '推送中' : '已下线' }}
                                </span>
                            </div>
                            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">{{ a.content }}</p>
                            <p class="text-xs text-gray-400 mt-1">{{ formatTime(a.created_at) }}</p>
                        </div>
                        <button
                            v-if="a.is_active"
                            @click="deactivate(a.id)"
                            class="px-3 py-1.5 rounded-lg text-xs text-red-500 border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/30 shrink-0 cursor-pointer"
                        >
                            下线
                        </button>
                    </div>
                </div>
            </div>
        </section>

        <!-- ============ 用户消息 ============ -->
        <section v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 用户列表 -->
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
                    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">选择目标用户（{{ userTotal }} 人）</h2>
                    <input
                        v-model="searchText"
                        type="text"
                        placeholder="按用户名或 ID 过滤"
                        class="mt-3 w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                </div>
                <div v-if="usersLoading" class="p-8 text-center text-gray-400 text-sm">加载中...</div>
                <div v-else-if="filteredUsers.length === 0" class="p-8 text-center text-gray-400 text-sm">无匹配用户</div>
                <div v-else class="divide-y divide-gray-100 dark:divide-gray-700 max-h-[420px] overflow-y-auto">
                    <button
                        v-for="u in filteredUsers"
                        :key="u.id"
                        @click="selectUser(u.id)"
                        class="w-full px-5 py-3 flex items-center justify-between text-left transition-colors cursor-pointer"
                        :class="selectedUserId === u.id
                            ? 'bg-indigo-50 dark:bg-indigo-900/30'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-900/40'"
                    >
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-bold flex items-center justify-center text-gray-500 dark:text-gray-400 shrink-0">
                                {{ u.username.charAt(0).toUpperCase() }}
                            </span>
                            <div class="min-w-0">
                                <p class="text-sm text-gray-800 dark:text-gray-100 truncate">{{ u.username }}</p>
                                <p class="text-xs text-gray-400">#{{ u.id }}</p>
                            </div>
                            <span v-if="u.is_admin" class="text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 shrink-0">管理</span>
                        </div>
                        <span v-if="selectedUserId === u.id" class="text-indigo-500 text-sm shrink-0">✓</span>
                    </button>
                </div>
            </div>

            <!-- 发送区 + 重置密码 -->
            <div class="space-y-6">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-5 h-fit">
                    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">发送管理员消息</h2>
                    <div class="mb-3">
                        <span class="text-xs text-gray-400">目标用户：</span>
                        <span v-if="selectedUserId !== null" class="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                            {{ users.find((u) => u.id === selectedUserId)?.username || `#${selectedUserId}` }}
                        </span>
                        <span v-else class="text-sm text-gray-400">未选择</span>
                    </div>
                    <textarea
                        v-model="msgContent"
                        placeholder="消息内容（1-500 字），发送后对方铃铛未读 +1"
                        maxlength="500"
                        rows="5"
                        class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y mb-3"
                    ></textarea>
                    <div class="flex items-center justify-between">
                        <span class="text-xs text-gray-400">{{ msgContent.length }}/500</span>
                        <button
                            @click="sendMessage"
                            :disabled="sending || selectedUserId === null || !msgContent.trim()"
                            class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                        >
                            {{ sending ? '发送中...' : '发送消息' }}
                        </button>
                    </div>
                </div>

                <!-- 重置用户密码 -->
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-5 h-fit">
                    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">重置用户密码</h2>
                    <div class="mb-3">
                        <span class="text-xs text-gray-400">目标用户：</span>
                        <span v-if="selectedUserId !== null" class="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                            {{ users.find((u) => u.id === selectedUserId)?.username || `#${selectedUserId}` }}
                        </span>
                        <span v-else class="text-sm text-gray-400">未选择</span>
                    </div>
                    <input
                        v-model="newPwd"
                        type="password"
                        placeholder="输入新密码"
                        class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-3"
                        autocomplete="new-password"
                    />
                    <!-- 成功提示 -->
                    <div v-if="resetSuccess" class="mb-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-600 dark:text-green-400 text-sm rounded-lg px-3 py-2">
                        {{ resetSuccess }}
                    </div>
                    <!-- 错误提示 -->
                    <div v-if="resetError" class="mb-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm rounded-lg px-3 py-2">
                        {{ resetError }}
                    </div>
                    <div class="flex justify-end">
                        <button
                            @click="handleResetPassword"
                            :disabled="resetting || selectedUserId === null || !newPwd.trim()"
                            class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                        >
                            {{ resetting ? '重置中...' : '重置密码' }}
                        </button>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>
