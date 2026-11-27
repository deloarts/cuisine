import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/shopping',
    name: 'shopping',
    component: () => import('@/features/shopping/views/ShoppingView.vue'),
    meta: { title: 'nav.shopping' },
  },
  {
    path: '/shopping/:id',
    name: 'shopping-list',
    component: () => import('@/features/shopping/views/ShoppingListView.vue'),
    meta: { title: 'nav.shopping' },
  },
] satisfies RouteRecordRaw[]
