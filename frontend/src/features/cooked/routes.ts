import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/cooked',
    name: 'cooked',
    component: () => import('@/features/cooked/views/CookedView.vue'),
    meta: { title: 'nav.cooked' },
  },
] satisfies RouteRecordRaw[]
