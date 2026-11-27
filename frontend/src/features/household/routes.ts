import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/household',
    name: 'household',
    component: () => import('@/features/household/views/HouseholdView.vue'),
    meta: { title: 'nav.household' },
  },
] satisfies RouteRecordRaw[]
