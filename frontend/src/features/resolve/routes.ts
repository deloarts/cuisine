import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/r/:publicId',
    name: 'resolve',
    component: () => import('@/features/resolve/views/ResolveView.vue'),
    meta: { title: 'resolve.title' },
  },
] satisfies RouteRecordRaw[]
