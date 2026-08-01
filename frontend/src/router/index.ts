import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from '../composables/useAuth'

const router = createRouter({
    history: createWebHistory(),
    routes:[
        {
            path: "/",
            name: "home",
            component: () => import ('../views/HomePage.vue'),
        },
        {
            path: "/types/:code",
            name: "type-detail",
            component: () => import ('../views/TypeDetailPage.vue'),
        },
        {
            path: "/books/:id",
            name: "book-detail",
            component: () => import ('../views/BookDetailPage.vue'),
        },
        {
            path: "/login",
            name: "login",
            component: () => import ('../views/LoginPage.vue'),
        },
        {
            path: "/register",
            name: "register",
            component: () => import ('../views/RegisterPage.vue'),
        },
        {
            path: "/forgot-password",
            name: "forgot-password",
            component: () => import ('../views/ForgotPasswordPage.vue'),
        },
        {
            path: "/reset-password",
            name: "reset-password",
            component: () => import ('../views/ResetPasswordPage.vue'),
        },
        {
            path: "/profile",
            name: "profile",
            meta: { requiresAuth: true },
            component: () => import ('../views/ProfilePage.vue'),
        },
        {
            path: "/notifications",
            name: "notifications",
            meta: { requiresAuth: true },
            component: () => import ('../views/NotificationsPage.vue'),
        },
        {
            path: "/admin",
            name: "admin",
            meta: { requiresAuth: true, requiresAdmin: true },
            component: () => import ('../views/AdminPage.vue'),
        },
    ],
})

// Navigation guard
router.beforeEach((to, _from, next) => {
    const { isLoggedIn, user } = useAuth()
    if ((to.path === '/login' || to.path === '/register') && isLoggedIn.value) {
        next('/')
    } else if (to.meta.requiresAuth && !isLoggedIn.value) {
        next('/login')
    } else if (to.meta.requiresAdmin && !user.value?.is_admin) {
        // 非管理员不可见：重定向首页，不暴露管理界面
        next('/')
    } else {
        next()
    }
})

export default router
