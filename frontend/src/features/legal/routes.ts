import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/legal/:kind(imprint|privacy)',
    name: 'legal',
    component: () => import('@/features/legal/views/LegalPageView.vue'),
    props: true,
    meta: { layout: 'public', requiresAuth: false },
  },
] satisfies RouteRecordRaw[]
