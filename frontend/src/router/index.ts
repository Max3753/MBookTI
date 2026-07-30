import { createRouter, createWebHistory } from "vue-router";

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
    ],
})

export default router
