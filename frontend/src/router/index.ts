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
            path: "/login",
            name: "login",
            component: () => import ('../views/LoginPage.vue'),
        },
        {
            path: "/register",
            name: "register",
            component: () => import ('../views/RegisterPage.vue'),
        },
    ],
})

// Navigation guard: redirect logged-in users away from auth pages
router.beforeEach((to, from, next) => {
    const { isLoggedIn } = useAuth()
    if ((to.path === '/login' || to.path === '/register') && isLoggedIn.value) {
        next('/')
    } else {
        next()
    }
})

export default router
