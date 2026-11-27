import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/kitchen',
    name: 'kitchen',
    component: () => import('@/features/kitchen/views/KitchenView.vue'),
    meta: { title: 'nav.myKitchen' },
  },
] satisfies RouteRecordRaw[]
