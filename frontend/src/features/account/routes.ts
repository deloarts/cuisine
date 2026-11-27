import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/account',
    name: 'account',
    component: () => import('@/features/account/views/AccountView.vue'),
    meta: { title: 'nav.account' },
  },
] satisfies RouteRecordRaw[]
