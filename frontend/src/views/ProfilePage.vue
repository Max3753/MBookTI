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
    uploadAvatar,
} from '../api'
import apiConfig, { resolveAssetUrl } from '../api/config'
import { useAuth } from '../composables/useAuth'
import { getMbtiTypes } from '../api'

const router = useRouter()
const { logout, updateUser } = useAuth()

const reloadPage = () => window.location.reload()

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
const editProfilePublic = ref(true)  // 公开主页开关（他人能否查看我的主页/书评/收藏）
const mbtiTypes = ref<any[]>([])
const saving = ref(false)
const saveMsg = ref('')

// 头像上传
const avatarUploading = ref(false)
const avatarMsg = ref('')
const avatarInputKey = ref(0)  // 强制重置 <input type=file>，允许重复选择同一文件
const avatarPreview = ref<string>('')  // 选中文件后的本地预览 URL
const pendingAvatarFile = ref<File | null>(null)  // 已选择、待上传的图片文件
let previewObjectUrl: string | null = null  // 追踪生成的 object URL 以便释放

function onAvatarPick(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    avatarMsg.value = ''
    // 把选中的文件规整为可直接上传的 File：
    // 支持格式（JPG/PNG/WebP/GIF）直接使用；HEIC 等移动端格式经 canvas 转码为 JPEG 再上传。
    prepareAvatarFile(file).then((prepared) => {
        if (!prepared) return
        pendingAvatarFile.value = prepared
        if (previewObjectUrl) {
            URL.revokeObjectURL(previewObjectUrl)
            previewObjectUrl = null
        }
        previewObjectUrl = URL.createObjectURL(prepared)
        avatarPreview.value = previewObjectUrl
        // 选择后立即上传，避免用户只点"保存"导致头像丢失
        submitAvatar()
    })
}

/** 校验并规整待上传图片：支持格式原样返回；不支持格式（如 HEIC）转码为 JPEG。 */
async function prepareAvatarFile(file: File): Promise<File | null> {
    const supported = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if (supported.includes(file.type)) {
        return file
    }
    // 非图片一律拒绝（用 createImageBitmap 兜底判断可解码性）
    if (!file.type.startsWith('image/')) {
        avatarMsg.value = '仅支持 JPG/PNG/WebP/GIF 图片'
        return null
    }
    // HEIC/HEIF 等移动端格式：canvas 转码 JPEG
    try {
        const bitmap = await createImageBitmap(file)
        const canvas = document.createElement('canvas')
        canvas.width = bitmap.width
        canvas.height = bitmap.height
        const ctx = canvas.getContext('2d')
        if (!ctx) throw new Error('no ctx')
        ctx.drawImage(bitmap, 0, 0)
        bitmap.close()
        const blob = await new Promise<Blob | null>((resolve) =>
            canvas.toBlob(resolve, 'image/jpeg', 0.92)
        )
        if (!blob) throw new Error('toBlob failed')
        return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' })
    } catch {
        avatarMsg.value = '无法识别该图片格式，请选择 JPG/PNG/WebP/GIF'
        return null
    }
}

/** 上传已选择的头像文件；无待上传文件时静默返回。 */
async function submitAvatar() {
    const file = pendingAvatarFile.value
    if (!file) return
    avatarUploading.value = true
    avatarMsg.value = ''
    try {
        const res = await uploadAvatar(file)
        profile.value = { ...profile.value, avatar_url: res.data.avatar_url }
        updateUser({ avatar_url: res.data.avatar_url })
        avatarMsg.value = '头像已更新'
        clearPendingAvatar()
    } catch (e: any) {
        avatarMsg.value = e.response?.data?.detail || '上传失败，请检查文件格式（JPG/PNG/WebP/GIF，≤2MB）'
        clearPendingAvatar()
    } finally {
        avatarUploading.value = false
    }
}

/** 清空待上传文件与预览（上传完成/失败后调用）。 */
function clearPendingAvatar() {
    pendingAvatarFile.value = null
    if (previewObjectUrl) {
        URL.revokeObjectURL(previewObjectUrl)
        previewObjectUrl = null
    }
    avatarPreview.value = ''
    avatarInputKey.value++
}

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
    editProfilePublic.value = profile.value?.is_profile_public ?? true
    saveMsg.value = ''
    editing.value = true
}

async function saveProfile() {
    if (!editUsername.value.trim()) return
    saving.value = true
    saveMsg.value = ''
    try {
        // 若头像仍在自动上传中，等待其完成，避免保存时头像丢失
        while (avatarUploading.value) {
            await new Promise((r) => setTimeout(r, 200))
        }
        const res = await updateMyProfile({
            username: editUsername.value.trim(),
            mbti_type_id: editMbtiId.value,
            is_profile_public: editProfilePublic.value,
        })
        profile.value = res.data
        // 同步共享用户状态（内存 ref + localStorage），导航栏/首页/类型页即时响应。
        // 不要直接写 localStorage：currentUser ref 只在模块加载时读一次，
        // 必须走 updateUser() 才能让本次会话内其他页面感知。
        updateUser({
            username: res.data.username,
            mbti_type_id: res.data.mbti_type_id,
            avatar_url: res.data.avatar_url,
        })
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
            <div class="np-card p-6">
                <div class="flex items-center gap-4">
                    <div class="w-16 h-16 border border-ink dark:border-paper bg-neutral-200 dark:bg-neutral-700"></div>
                    <div class="flex-1 space-y-2">
                        <div class="h-5 bg-neutral-200 dark:bg-neutral-700 w-1/3"></div>
                        <div class="h-3 bg-neutral-200 dark:bg-neutral-700 w-1/2"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="error" class="text-center py-20">
            <p class="font-serif text-2xl text-neutral-400 mb-4">{{ error }}</p>
            <button @click="reloadPage" class="np-btn-link text-sm cursor-pointer">重试</button>
        </div>

        <div v-else-if="profile" class="space-y-6">
            <!-- 头部卡片：读者档案 -->
            <div class="np-card p-6 animate-newsprint-in">
                <div class="flex flex-col sm:flex-row sm:items-start gap-5">
                    <!-- 头像：有 avatar_url 显示图片，否则显示首字母墨印 -->
                    <div class="w-16 h-16 shrink-0 flex items-center justify-center text-2xl font-serif font-bold text-white border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                        <img v-if="profile.avatar_url" :src="resolveAssetUrl(profile.avatar_url)" :alt="profile.username"
                            class="w-full h-full object-cover" />
                        <template v-else>
                            <div class="w-full h-full flex items-center justify-center" :class="avatarColor">
                                {{ (profile.username || '?')[0].toUpperCase() }}
                            </div>
                        </template>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-3 flex-wrap">
                            <h1 class="font-serif text-3xl font-bold tracking-tight truncate">{{ profile.username }}</h1>
                            <span v-if="profile.mbti_type_code" class="np-badge np-badge-editorial shrink-0">
                                {{ profile.mbti_type_code }} {{ profile.mbti_type_name }}
                            </span>
                        </div>
                        <p class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">{{ profile.email }}</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-1">
                            注册于 {{ new Date(profile.created_at).toLocaleDateString('zh-CN') }}
                        </p>
                    </div>
                    <!-- 操作按钮：移动端换行到下一行 -->
                    <div class="flex gap-2 shrink-0 sm:ml-auto">
                        <router-link :to="`/users/${profile.id}`" class="np-btn np-btn-ghost px-4">公开主页</router-link>
                        <button @click="openEdit" class="np-btn np-btn-secondary px-4 cursor-pointer">编辑资料</button>
                        <button @click="openPw" class="np-btn np-btn-primary px-4 cursor-pointer">改密码</button>
                    </div>
                </div>

                <!-- 电子书阅读器入口：独立横条，报纸风格分隔 -->
                <div class="mt-6 flex items-center justify-between gap-4 border-t-2 border-ink dark:border-paper pt-5">
                    <div>
                        <h2 class="font-serif text-lg font-bold text-ink dark:text-paper">电子书阅读器</h2>
                        <p class="edition-label text-neutral-500 dark:text-neutral-400 mt-1">支持 EPUB / TXT 在线阅读，自动保存阅读进度</p>
                    </div>
                    <router-link to="/reader" class="np-btn np-btn-ghost px-4 shrink-0">打开阅读器</router-link>
                </div>

                <!-- 统计徽章：报纸数据栏（5 列，与公开主页口径一致） -->
                <div class="grid grid-cols-5 border border-ink dark:border-paper mt-6">
                    <div class="py-4 text-center border-r border-ink dark:border-paper">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.comment_count }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">书评</div>
                    </div>
                    <div class="py-4 text-center border-r border-ink dark:border-paper">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.favorite_count }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">收藏</div>
                    </div>
                    <div class="py-4 text-center border-r border-ink dark:border-paper">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.like_received }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">获赞</div>
                    </div>
                    <div class="py-4 text-center border-r border-ink dark:border-paper">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.follower_count ?? 0 }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">粉丝</div>
                    </div>
                    <div class="py-4 text-center">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.following_count ?? 0 }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">关注</div>
                    </div>
                </div>

                <!-- 编辑资料弹窗 -->
                <div v-if="editing" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="editing = false">
                    <div class="np-card p-6 w-full max-w-sm animate-newsprint-in">
                        <h3 class="font-serif text-xl font-bold border-b-4 border-ink dark:border-paper pb-2 mb-5">编辑资料</h3>

                        <!-- 头像更换 -->
                        <label class="edition-label text-neutral-500 dark:text-neutral-400 block mb-1">头像</label>
                        <div class="flex items-center gap-4 mb-4">
                            <div class="w-14 h-14 shrink-0 flex items-center justify-center text-xl font-serif font-bold text-white border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                                <img v-if="avatarPreview" :src="avatarPreview" alt="预览" class="w-full h-full object-cover" />
                                <img v-else-if="profile.avatar_url" :src="resolveAssetUrl(profile.avatar_url)" alt="当前头像" class="w-full h-full object-cover" />
                                <div v-else class="w-full h-full flex items-center justify-center" :class="avatarColor">
                                    {{ (profile.username || '?')[0].toUpperCase() }}
                                </div>
                            </div>
                            <div class="flex-1 min-w-0">
                                <input :key="avatarInputKey" id="avatar-file-input" type="file" accept="image/*"
                                    @change="onAvatarPick" class="block w-full text-xs text-neutral-500 dark:text-neutral-400
                                    file:mr-3 file:px-3 file:py-1.5 file:border file:border-ink dark:file:border-paper
                                    file:bg-ink file:text-paper dark:file:bg-paper dark:file:text-ink file:font-sans file:text-xs file:cursor-pointer" />
                                <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-1">JPG / PNG / WebP / GIF（HEIC 自动转码），不超过 2MB</p>
                            </div>
                        </div>
                        <div class="flex items-center justify-between mb-4">
                            <span class="edition-label text-neutral-400 dark:text-neutral-500">
                                {{ avatarUploading ? '上传中...' : '选择图片后自动上传' }}
                            </span>
                            <p v-if="avatarMsg" class="font-mono text-xs truncate"
                                :class="avatarMsg === '头像已更新' ? 'text-neutral-500 dark:text-neutral-400' : 'text-editorial'">
                                {{ avatarMsg }}
                            </p>
                        </div>

                        <label class="edition-label text-neutral-500 dark:text-neutral-400 block mb-1">用户名</label>
                        <input v-model="editUsername" type="text" class="np-input mb-4" />
                        <label class="edition-label text-neutral-500 dark:text-neutral-400 block mb-1">我的 MBTI 类型</label>
                        <select v-model="editMbtiId" class="np-input cursor-pointer mb-5">
                            <option :value="null">未设置</option>
                            <option v-for="mt in mbtiTypes" :key="mt.id" :value="mt.id">{{ mt.code }} {{ mt.name }}</option>
                        </select>

                        <!-- 公开主页开关 -->
                        <label class="flex items-center justify-between border border-ink/15 dark:border-paper/20 px-3 py-3 mb-5 cursor-pointer">
                            <span>
                                <span class="block text-sm font-semibold text-ink dark:text-paper">公开我的主页</span>
                                <span class="block edition-label text-neutral-400 dark:text-neutral-500 mt-0.5">
                                    {{ editProfilePublic ? '任何人可查看我的主页 / 书评 / 收藏' : '仅自己可见（他人访问显示不存在）' }}
                                </span>
                            </span>
                            <span class="relative inline-flex items-center h-6 w-11 shrink-0 rounded-full transition-colors"
                                :class="editProfilePublic ? 'bg-editorial' : 'bg-neutral-300 dark:bg-neutral-600'">
                                <input type="checkbox" v-model="editProfilePublic" class="sr-only" />
                                <span class="inline-block w-4 h-4 bg-paper rounded-full shadow transition-transform"
                                    :class="editProfilePublic ? 'translate-x-6' : 'translate-x-1'"></span>
                            </span>
                        </label>
                        <p v-if="saveMsg" class="font-mono text-xs mb-3"
                            :class="saveMsg === '已保存' ? 'text-neutral-500 dark:text-neutral-400' : 'text-editorial'">
                            {{ saveMsg }}
                        </p>
                        <div class="flex gap-2 justify-end">
                            <button @click="editing = false" class="np-btn np-btn-secondary px-5 cursor-pointer">取消</button>
                            <button @click="saveProfile" :disabled="saving"
                                class="np-btn np-btn-primary px-5 cursor-pointer">
                                {{ saving ? '保存中...' : '保存' }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 改密码弹窗 -->
                <div v-if="pwOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="pwOpen = false">
                    <div class="np-card p-6 w-full max-w-sm animate-newsprint-in">
                        <h3 class="font-serif text-xl font-bold border-b-4 border-ink dark:border-paper pb-2 mb-5">修改密码</h3>
                        <input v-model="oldPassword" type="password" placeholder="旧密码" class="np-input mb-4" />
                        <input v-model="newPassword" type="password" placeholder="新密码" class="np-input mb-4" />
                        <input v-model="confirmPassword" type="password" placeholder="确认新密码" class="np-input mb-5" />
                        <p v-if="pwError" class="font-mono text-xs text-editorial mb-3">{{ pwError }}</p>
                        <div class="flex gap-2 justify-end">
                            <button @click="pwOpen = false" class="np-btn np-btn-secondary px-5 cursor-pointer">取消</button>
                            <button @click="submitPassword" :disabled="pwSubmitting"
                                class="np-btn np-btn-primary px-5 cursor-pointer">
                                {{ pwSubmitting ? '提交中...' : '确认修改' }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tabs：报纸栏目切换 -->
            <div class="np-card animate-newsprint-in">
                <div class="flex border-b-2 border-ink dark:border-paper">
                    <button @click="switchTab('comments')"
                        class="flex-1 py-3 text-sm font-sans uppercase tracking-widest border-b-4 -mb-0.5 transition-colors cursor-pointer"
                        :class="activeTab === 'comments'
                            ? 'border-editorial text-ink dark:text-paper font-semibold'
                            : 'border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'">
                        我的书评 ({{ profile.stats.comment_count }})
                    </button>
                    <button @click="switchTab('favorites')"
                        class="flex-1 py-3 text-sm font-sans uppercase tracking-widest border-b-4 -mb-0.5 transition-colors cursor-pointer"
                        :class="activeTab === 'favorites'
                            ? 'border-editorial text-ink dark:text-paper font-semibold'
                            : 'border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'">
                        我的收藏 ({{ profile.stats.favorite_count }})
                    </button>
                </div>

                <!-- 书评 Tab -->
                <div v-if="activeTab === 'comments'">
                    <div v-if="commentsLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="comments.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">暂无书评</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">去书籍详情页写下第一条吧</p>
                    </div>
                    <div v-for="c in comments" :key="c.id"
                        class="p-4 flex gap-3 border-b border-divider dark:border-paper/40 last:border-b-0 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 transition-colors">
                        <router-link :to="`/books/${c.book_id}`"
                            class="w-12 h-16 border border-ink dark:border-paper overflow-hidden shrink-0 bg-neutral-100 dark:bg-neutral-800">
                            <img v-if="c.book_cover_url" :src="proxyUrl(c.book_cover_url)" :alt="c.book_title"
                                class="w-full h-full object-cover newsprint-img" />
                            <div v-else class="w-full h-full halftone"></div>
                        </router-link>
                        <div class="flex-1 min-w-0">
                            <router-link :to="`/books/${c.book_id}`" class="np-btn-link text-sm">《{{ c.book_title }}》</router-link>
                            <p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1 line-clamp-2 font-body">{{ c.content }}</p>
                            <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-1.5">
                                {{ new Date(c.created_at).toLocaleString('zh-CN') }} · ♥ {{ c.likes_count }}
                            </p>
                        </div>
                        <button @click="removeComment(c.id)" :disabled="deletingId === c.id"
                            class="text-xs font-sans text-editorial hover:underline underline-offset-4 disabled:opacity-50 shrink-0 cursor-pointer">
                            {{ deletingId === c.id ? '删除中...' : '删除' }}
                        </button>
                    </div>
                </div>

                <!-- 收藏 Tab -->
                <div v-else class="p-4">
                    <div v-if="favoritesLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="favorites.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">暂无收藏</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">去书籍详情页点 ♡ 收藏吧</p>
                    </div>
                    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                        <router-link v-for="b in favorites" :key="b.id" :to="`/books/${b.id}`"
                            class="np-card np-card-hover p-3 block">
                            <div class="w-full h-32 border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800 mb-2">
                                <img v-if="b.cover_url" :src="proxyUrl(b.cover_url)" :alt="b.title"
                                    class="w-full h-full object-cover newsprint-img" />
                                <div v-else class="w-full h-full halftone"></div>
                            </div>
                            <div class="text-sm font-medium font-serif truncate text-ink dark:text-paper">{{ b.title }}</div>
                            <div class="edition-label text-neutral-400 dark:text-neutral-500 mt-0.5 truncate">{{ b.author }}</div>
                        </router-link>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
