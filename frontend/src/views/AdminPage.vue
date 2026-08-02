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
    <div class="space-y-6">
        <!-- 报头 -->
        <header class="animate-newsprint-in">
            <div class="flex items-center justify-between border-b border-ink/30 dark:border-paper/30 pb-1.5 mb-2 edition-label text-neutral-500 dark:text-neutral-400">
                <span>MBookTI · 编辑部 · ADMIN DESK</span>
                <span class="text-editorial font-semibold">★ 今日排印</span>
            </div>
            <h1 class="font-serif text-4xl sm:text-5xl font-black tracking-tighter border-b-4 border-editorial pb-3">管理后台</h1>
        </header>

        <!-- Tab 切换 -->
        <div class="flex mb-6">
            <button
                @click="activeTab = 'announcements'"
                class="np-btn cursor-pointer"
                :class="activeTab === 'announcements' ? 'np-btn-primary' : 'np-btn-ghost'"
            >
                公告管理
            </button>
            <div class="w-px bg-ink/30 dark:bg-paper/30"></div>
            <button
                @click="activeTab = 'messages'"
                class="np-btn cursor-pointer"
                :class="activeTab === 'messages' ? 'np-btn-primary' : 'np-btn-ghost'"
            >
                用户消息
            </button>
        </div>

        <!-- ============ 公告管理 ============ -->
        <section v-if="activeTab === 'announcements'" class="space-y-6">
            <!-- 发布表单 -->
            <div class="np-card p-6 animate-newsprint-in">
                <div class="flex items-center justify-between border-b-2 border-ink dark:border-paper pb-2 mb-5">
                    <h2 class="font-serif text-xl font-bold tracking-tight">发布系统公告</h2>
                    <span class="edition-label text-editorial">NOTICE BOARD</span>
                </div>
                <input
                    v-model="annTitle"
                    type="text"
                    placeholder="公告标题（1-100 字）"
                    maxlength="100"
                    class="np-input mb-4"
                />
                <textarea
                    v-model="annContent"
                    placeholder="公告内容（1-5000 字）"
                    maxlength="5000"
                    rows="4"
                    class="np-input border-2 border-ink dark:border-paper mb-3 resize-y"
                ></textarea>
                <div class="flex items-center justify-between">
                    <span class="edition-label text-neutral-400 dark:text-neutral-500">{{ annContent.length }}/5000</span>
                    <button
                        @click="publish"
                        :disabled="publishing || !annTitle.trim() || !annContent.trim()"
                        class="np-btn np-btn-primary !min-h-[36px] !px-4"
                    >
                        {{ publishing ? '发布中...' : '发布公告' }}
                    </button>
                </div>
            </div>

            <!-- 已发布列表 -->
            <div class="np-card overflow-hidden animate-newsprint-in">
                <div class="px-5 py-4 border-b-2 border-ink dark:border-paper flex items-center justify-between">
                    <h2 class="font-serif text-lg font-bold tracking-tight">已发布公告</h2>
                    <span class="edition-label text-neutral-500 dark:text-neutral-400">{{ annTotal }} 条</span>
                </div>
                <div v-if="annLoading" class="p-10 text-center">
                    <span class="edition-label text-neutral-400">加载中…</span>
                </div>
                <div v-else-if="announcements.length === 0" class="p-10 text-center">
                    <span class="edition-label text-neutral-400">暂无公告</span>
                </div>
                <table v-else class="np-table w-full">
                    <thead>
                        <tr>
                            <th class="edition-label !font-mono">公告标题</th>
                            <th class="edition-label !font-mono">状态</th>
                            <th class="edition-label !font-mono">发布时间</th>
                            <th class="edition-label !font-mono !text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="a in announcements" :key="a.id" class="align-top">
                            <td>
                                <div class="font-serif font-bold text-ink dark:text-paper">{{ a.title }}</div>
                                <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">{{ a.content }}</p>
                            </td>
                            <td>
                                <span
                                    class="np-badge"
                                    :class="a.is_active ? 'np-badge-editorial' : 'np-badge-outline'"
                                >
                                    {{ a.is_active ? '推送中' : '已下线' }}
                                </span>
                            </td>
                            <td class="!font-mono text-neutral-500 dark:text-neutral-400 whitespace-nowrap">{{ formatTime(a.created_at) }}</td>
                            <td class="text-right">
                                <button
                                    v-if="a.is_active"
                                    @click="deactivate(a.id)"
                                    class="np-btn np-btn-secondary !min-h-[32px] !px-3"
                                >
                                    下线
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- ============ 用户消息 ============ -->
        <section v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 用户列表 -->
            <div class="np-card overflow-hidden animate-newsprint-in">
                <div class="px-5 py-4 border-b-2 border-ink dark:border-paper">
                    <div class="flex items-center justify-between">
                        <h2 class="font-serif text-lg font-bold tracking-tight">选择目标用户</h2>
                        <span class="edition-label text-neutral-500 dark:text-neutral-400">{{ userTotal }} 人</span>
                    </div>
                    <input
                        v-model="searchText"
                        type="text"
                        placeholder="按用户名或 ID 过滤"
                        class="np-input mt-4"
                    />
                </div>
                <div v-if="usersLoading" class="p-10 text-center">
                    <span class="edition-label text-neutral-400">加载中…</span>
                </div>
                <div v-else-if="filteredUsers.length === 0" class="p-10 text-center">
                    <span class="edition-label text-neutral-400">无匹配用户</span>
                </div>
                <div v-else class="max-h-[420px] overflow-y-auto">
                    <table class="np-table w-full">
                        <thead>
                            <tr>
                                <th class="edition-label !font-mono">用户</th>
                                <th class="edition-label !font-mono">ID</th>
                                <th class="edition-label !font-mono">角色</th>
                                <th class="edition-label !font-mono !text-right">选择</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="u in filteredUsers"
                                :key="u.id"
                                @click="selectUser(u.id)"
                                class="cursor-pointer"
                                :class="selectedUserId === u.id
                                    ? 'bg-neutral-100 dark:bg-neutral-700/50'
                                    : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/30'"
                            >
                                <td>
                                    <div class="flex items-center gap-2 min-w-0">
                                        <span class="w-8 h-8 border border-ink dark:border-paper text-xs font-mono font-bold flex items-center justify-center text-ink dark:text-paper shrink-0">
                                            {{ u.username.charAt(0).toUpperCase() }}
                                        </span>
                                        <span class="font-medium text-ink dark:text-paper truncate">{{ u.username }}</span>
                                    </div>
                                </td>
                                <td class="!font-mono text-neutral-500 dark:text-neutral-400">#{{ u.id }}</td>
                                <td>
                                    <span v-if="u.is_admin" class="np-badge np-badge-outline">管理</span>
                                    <span v-else class="edition-label text-neutral-400 dark:text-neutral-500">读者</span>
                                </td>
                                <td class="text-right">
                                    <span v-if="selectedUserId === u.id" class="font-mono font-bold text-editorial">✓</span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 发送区 + 重置密码 -->
            <div class="space-y-6">
                <div class="np-card p-6 h-fit animate-newsprint-in">
                    <div class="flex items-center justify-between border-b-2 border-ink dark:border-paper pb-2 mb-5">
                        <h2 class="font-serif text-xl font-bold tracking-tight">发送管理员消息</h2>
                        <span class="edition-label text-editorial">DESPATCH</span>
                    </div>
                    <div class="mb-3 flex items-center gap-2">
                        <span class="edition-label text-neutral-500 dark:text-neutral-400">目标用户</span>
                        <span v-if="selectedUserId !== null" class="font-mono text-sm font-semibold text-editorial">
                            {{ users.find((u) => u.id === selectedUserId)?.username || `#${selectedUserId}` }}
                        </span>
                        <span v-else class="font-mono text-sm text-neutral-400">未选择</span>
                    </div>
                    <textarea
                        v-model="msgContent"
                        placeholder="消息内容（1-500 字），发送后对方铃铛未读 +1"
                        maxlength="500"
                        rows="5"
                        class="np-input border-2 border-ink dark:border-paper mb-3 resize-y"
                    ></textarea>
                    <div class="flex items-center justify-between">
                        <span class="edition-label text-neutral-400 dark:text-neutral-500">{{ msgContent.length }}/500</span>
                        <button
                            @click="sendMessage"
                            :disabled="sending || selectedUserId === null || !msgContent.trim()"
                            class="np-btn np-btn-primary !min-h-[36px] !px-4"
                        >
                            {{ sending ? '发送中...' : '发送消息' }}
                        </button>
                    </div>
                </div>

                <!-- 重置用户密码 -->
                <div class="np-card p-6 h-fit animate-newsprint-in">
                    <div class="flex items-center justify-between border-b-2 border-ink dark:border-paper pb-2 mb-5">
                        <h2 class="font-serif text-xl font-bold tracking-tight">重置用户密码</h2>
                        <span class="edition-label text-editorial">SECURITY DESK</span>
                    </div>
                    <div class="mb-3 flex items-center gap-2">
                        <span class="edition-label text-neutral-500 dark:text-neutral-400">目标用户</span>
                        <span v-if="selectedUserId !== null" class="font-mono text-sm font-semibold text-editorial">
                            {{ users.find((u) => u.id === selectedUserId)?.username || `#${selectedUserId}` }}
                        </span>
                        <span v-else class="font-mono text-sm text-neutral-400">未选择</span>
                    </div>
                    <input
                        v-model="newPwd"
                        type="password"
                        placeholder="输入新密码"
                        class="np-input mb-3"
                        autocomplete="new-password"
                    />
                    <!-- 成功提示 -->
                    <div v-if="resetSuccess" class="mb-3 border-2 border-ink text-ink dark:border-paper dark:text-paper text-sm px-4 py-3 font-mono">
                        ✓ {{ resetSuccess }}
                    </div>
                    <!-- 错误提示 -->
                    <div v-if="resetError" class="mb-3 border-2 border-editorial text-editorial text-sm px-4 py-3 font-mono">
                        ✗ {{ resetError }}
                    </div>
                    <div class="flex justify-end">
                        <button
                            @click="handleResetPassword"
                            :disabled="resetting || selectedUserId === null || !newPwd.trim()"
                            class="np-btn np-btn-primary !min-h-[36px] !px-4"
                        >
                            {{ resetting ? '重置中...' : '重置密码' }}
                        </button>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>
