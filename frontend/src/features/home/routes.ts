import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/',
    name: 'home',
    component: () => import('@/features/home/views/HomeView.vue'),
    meta: { title: 'nav.home' },
  },
] satisfies RouteRecordRaw[]
