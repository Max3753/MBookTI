<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
    getPublicUserProfile,
    getUserComments,
    getUserFavorites,
    toggleFollow,
    getFollowers,
    getFollowing,
} from '../api'
import apiConfig, { resolveAssetUrl } from '../api/config'
import { useAuth } from '../composables/useAuth'

interface UserStats {
    comment_count: number
    favorite_count: number
    like_received: number
    follower_count: number
    following_count: number
}

interface PublicUserProfile {
    id: number
    username: string
    avatar_url: string | null
    is_admin: boolean
    is_profile_public: boolean
    created_at: string
    mbti_type_code: string | null
    mbti_type_name: string | null
    stats: UserStats
    is_following: boolean
    is_self: boolean
}

interface UserComment {
    id: number
    book_id: number
    book_title: string
    book_cover_url: string | null
    parent_id: number | null
    content: string
    likes_count: number
    created_at: string
}

interface FavoriteBook {
    id: number
    title: string
    author: string
    cover_url: string | null
}

interface FollowUser {
    id: number
    username: string
    avatar_url: string | null
}

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAuth()

// 路由参数变化时组件会被整体重建（App.vue 以 $route.fullPath 为 key），无需 watch
const userId = Number(route.params.id)

const profile = ref<PublicUserProfile | null>(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref<'comments' | 'favorites' | 'followers' | 'following'>('comments')

// 关注切换
const following = ref(false)

// 书评
const comments = ref<UserComment[]>([])
const commentsLoading = ref(false)

// 收藏
const favorites = ref<FavoriteBook[]>([])
const favoritesLoading = ref(false)

// 粉丝 / 关注
const followers = ref<FollowUser[]>([])
const followersLoading = ref(false)
const followingList = ref<FollowUser[]>([])
const followingLoading = ref(false)

// 默认头像色板
const avatarPalette = [
    'bg-indigo-500', 'bg-pink-500', 'bg-emerald-500', 'bg-amber-500',
    'bg-sky-500', 'bg-purple-500', 'bg-rose-500', 'bg-teal-500',
]
function avatarColorFor(name: string): string {
    return avatarPalette[name.charCodeAt(0) % avatarPalette.length]
}
const avatarColor = computed(() => avatarColorFor(profile.value?.username || '?'))

// 豆瓣封面代理（图床防盗链，走后端代理）
function proxyUrl(url: string): string {
    if (!url) return ''
    return `${apiConfig.baseURL}/proxy/cover?url=${encodeURIComponent(url)}`
}

// 相对时间（与 BookDetailPage 同款）
function timeAgo(dateStr: string): string {
    const now = Date.now()
    const date = new Date(dateStr).getTime()
    const diff = Math.floor((now - date) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    const days = Math.floor(diff / 86400)
    if (days < 30) return `${days}天前`
    return new Date(dateStr).toLocaleDateString('zh-CN')
}

// 返回：基于 vue-router 记录的来源路由，避免依赖浏览器历史栈
function goBack() {
    const back = (window.history.state?.back as string) || ''
    if (back.startsWith('/') && back !== '/') {
        router.push(back)
    } else {
        router.push('/')
    }
}

async function loadProfile() {
    try {
        const res = await getPublicUserProfile(userId)
        profile.value = res.data
    } catch {
        error.value = '没有找到这位读者'
    } finally {
        loading.value = false
    }
}

async function loadComments() {
    commentsLoading.value = true
    try {
        const res = await getUserComments(userId, 1, 20)
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
        const res = await getUserFavorites(userId)
        favorites.value = res.data || []
    } catch {
        favorites.value = []
    } finally {
        favoritesLoading.value = false
    }
}

async function loadFollowers() {
    followersLoading.value = true
    try {
        const res = await getFollowers(userId, 1, 50)
        followers.value = res.data || []
    } catch {
        followers.value = []
    } finally {
        followersLoading.value = false
    }
}

async function loadFollowing() {
    followingLoading.value = true
    try {
        const res = await getFollowing(userId, 1, 50)
        followingList.value = res.data || []
    } catch {
        followingList.value = []
    } finally {
        followingLoading.value = false
    }
}

function switchTab(tab: 'comments' | 'favorites' | 'followers' | 'following') {
    activeTab.value = tab
    if (tab === 'comments' && comments.value.length === 0 && !commentsLoading.value) {
        loadComments()
    }
    if (tab === 'favorites' && favorites.value.length === 0 && !favoritesLoading.value) {
        loadFavorites()
    }
    if (tab === 'followers' && followers.value.length === 0 && !followersLoading.value) {
        loadFollowers()
    }
    if (tab === 'following' && followingList.value.length === 0 && !followingLoading.value) {
        loadFollowing()
    }
}

// 关注 / 取消关注（后端为 toggle）。未登录点击跳转登录页。
async function handleFollow() {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (following.value) return
    following.value = true
    try {
        await toggleFollow(userId)
        // 关注/取消后全量重拉主页数据，保证粉丝数/关注关系与后端一致（不做手动 ±1，避免边界不一致）
        await loadProfile()
        // 若当前停在粉丝/关注 Tab，同步刷新列表（让自己出现在/消失于列表中）
        if (activeTab.value === 'followers') {
            await loadFollowers()
        } else if (activeTab.value === 'following') {
            await loadFollowing()
        }
    } catch {
        // 失败保持原状
    } finally {
        following.value = false
    }
}

onMounted(async () => {
    await loadProfile()
    loadComments()
})
</script>

<template>
    <div>
        <!-- 返回按钮 -->
        <button @click="goBack" class="mb-6 flex items-center gap-1.5 np-btn np-btn-ghost px-3 text-sm cursor-pointer">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            <span class="edition-label">返回 · BACK</span>
        </button>

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
            <div class="mx-auto max-w-md np-card px-8 py-10">
                <div class="edition-label text-editorial mb-3">查无此人 · NOT FOUND</div>
                <p class="font-serif text-2xl font-bold text-ink dark:text-paper mb-6">{{ error }}</p>
                <button @click="goBack" class="np-btn np-btn-primary cursor-pointer">返回</button>
            </div>
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
                            <!-- 这是自己的主页：不显示关注按钮 -->
                            <span v-if="profile.is_self" class="np-badge np-badge-editorial shrink-0">这是你</span>
                            <span v-if="profile.is_self" class="np-badge shrink-0"
                                :class="profile.is_profile_public ? 'np-badge-outline' : 'np-badge-editorial'">
                                {{ profile.is_profile_public ? '主页公开' : '仅自己可见' }}
                            </span>
                            <span v-if="profile.mbti_type_name" class="np-badge np-badge-editorial shrink-0">
                                {{ profile.mbti_type_code }} {{ profile.mbti_type_name }}
                            </span>
                        </div>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-1">
                            注册于 {{ new Date(profile.created_at).toLocaleDateString('zh-CN') }}
                        </p>
                    </div>
                    <!-- 操作区：自己 → 跳转个人中心；他人 → 关注/已关注 -->
                    <div class="flex gap-2 shrink-0 sm:ml-auto">
                        <router-link v-if="profile.is_self" to="/profile" class="np-btn np-btn-secondary px-4">查看我的主页</router-link>
                        <button v-else @click="handleFollow" :disabled="following"
                            class="np-btn px-4 cursor-pointer"
                            :class="profile.is_following ? 'np-btn-secondary' : 'np-btn-primary'">
                            {{ following ? '处理中...' : profile.is_following ? '已关注' : '关注' }}
                        </button>
                    </div>
                </div>

                <!-- 统计徽章：报纸数据栏（5 列：书评/收藏/获赞/粉丝/关注） -->
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
                    <button @click="switchTab('followers')" class="py-4 text-center border-r border-ink dark:border-paper cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800/60 transition-colors">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.follower_count }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">粉丝</div>
                    </button>
                    <button @click="switchTab('following')" class="py-4 text-center cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800/60 transition-colors">
                        <div class="font-mono text-2xl sm:text-3xl font-medium leading-none">{{ profile.stats.following_count }}</div>
                        <div class="edition-label text-neutral-500 dark:text-neutral-400 mt-2">关注</div>
                    </button>
                </div>
            </div>

            <!-- Tabs：报纸栏目切换 -->
            <div class="np-card animate-newsprint-in">
                <div class="flex border-b-2 border-ink dark:border-paper">
                    <button v-for="tab in ([
                        { key: 'comments', label: '书评' },
                        { key: 'favorites', label: '收藏' },
                        { key: 'followers', label: '粉丝' },
                        { key: 'following', label: '关注' },
                    ] as const)" :key="tab.key" @click="switchTab(tab.key)"
                        class="flex-1 py-3 text-sm font-sans uppercase tracking-widest border-b-4 -mb-0.5 transition-colors cursor-pointer"
                        :class="activeTab === tab.key
                            ? 'border-editorial text-ink dark:text-paper font-semibold'
                            : 'border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'">
                        {{ tab.label }} ({{ tab.key === 'comments' ? profile.stats.comment_count
                            : tab.key === 'favorites' ? profile.stats.favorite_count
                            : tab.key === 'followers' ? profile.stats.follower_count
                            : profile.stats.following_count }})
                    </button>
                </div>

                <!-- 书评 Tab -->
                <div v-if="activeTab === 'comments'">
                    <div v-if="commentsLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="comments.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">暂无书评</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">这位读者还没有发表过书评</p>
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
                            <div class="flex items-center gap-2">
                                <router-link :to="`/books/${c.book_id}`" class="np-btn-link text-sm">《{{ c.book_title }}》</router-link>
                                <span v-if="c.parent_id" class="np-badge np-badge-outline leading-none shrink-0">回复</span>
                            </div>
                            <p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1 line-clamp-2 font-body">{{ c.content }}</p>
                            <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-1.5">
                                {{ timeAgo(c.created_at) }} · ♥ {{ c.likes_count }}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- 收藏 Tab -->
                <div v-else-if="activeTab === 'favorites'" class="p-4">
                    <div v-if="favoritesLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="favorites.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">暂无收藏</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">这位读者还没有收藏任何书籍</p>
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

                <!-- 粉丝 Tab -->
                <div v-else-if="activeTab === 'followers'">
                    <div v-if="followersLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="followers.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">还没有粉丝</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">成为他/她的第一个读者吧</p>
                    </div>
                    <router-link v-for="u in followers" :key="u.id" :to="`/users/${u.id}`"
                        class="p-4 flex items-center gap-3 border-b border-divider dark:border-paper/40 last:border-b-0 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 transition-colors">
                        <div class="w-10 h-10 shrink-0 flex items-center justify-center text-sm font-bold text-white border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                            <img v-if="u.avatar_url" :src="resolveAssetUrl(u.avatar_url)" :alt="u.username" class="w-full h-full object-cover" />
                            <div v-else class="w-full h-full flex items-center justify-center" :class="avatarColorFor(u.username)">
                                {{ (u.username || '?')[0].toUpperCase() }}
                            </div>
                        </div>
                        <span class="text-sm font-semibold text-ink dark:text-paper truncate">{{ u.username }}</span>
                    </router-link>
                </div>

                <!-- 关注 Tab -->
                <div v-else>
                    <div v-if="followingLoading" class="p-6 text-center edition-label text-neutral-400">加载中...</div>
                    <div v-else-if="followingList.length === 0" class="p-12 text-center">
                        <p class="font-serif text-2xl text-neutral-400">还没有关注任何人</p>
                        <p class="edition-label text-neutral-400 dark:text-neutral-500 mt-3">去看看大家的书评吧</p>
                    </div>
                    <router-link v-for="u in followingList" :key="u.id" :to="`/users/${u.id}`"
                        class="p-4 flex items-center gap-3 border-b border-divider dark:border-paper/40 last:border-b-0 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 transition-colors">
                        <div class="w-10 h-10 shrink-0 flex items-center justify-center text-sm font-bold text-white border border-ink dark:border-paper overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                            <img v-if="u.avatar_url" :src="resolveAssetUrl(u.avatar_url)" :alt="u.username" class="w-full h-full object-cover" />
                            <div v-else class="w-full h-full flex items-center justify-center" :class="avatarColorFor(u.username)">
                                {{ (u.username || '?')[0].toUpperCase() }}
                            </div>
                        </div>
                        <span class="text-sm font-semibold text-ink dark:text-paper truncate">{{ u.username }}</span>
                    </router-link>
                </div>
            </div>
        </div>
    </div>
</template>
