import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/views/LoginView.vue'),
    meta: { layout: 'auth', requiresAuth: false, title: 'auth.title' },
  },
] satisfies RouteRecordRaw[]
