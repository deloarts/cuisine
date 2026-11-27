import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/resources/:tab?',
    name: 'resources',
    component: () => import('@/features/resources/views/ResourcesView.vue'),
    meta: { title: 'nav.resources' },
  },
] satisfies RouteRecordRaw[]
