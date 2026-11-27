import type { RouteRecordRaw } from 'vue-router'

import { ADMIN_PERMISSIONS } from '@/features/admin-settings/adminTabs'

export default [
  {
    path: '/admin/:tab?',
    name: 'admin',
    component: () => import('@/features/admin-settings/views/AdminView.vue'),
    meta: { title: 'nav.admin', permissions: ADMIN_PERMISSIONS },
  },
  // The pages before the admin area had tabs; /admin/users and /admin/groups
  // already resolve to their tabs.
  { path: '/admin/settings', redirect: { name: 'admin', params: { tab: 'general' } } },
  { path: '/settings/:tab?', redirect: (to) => ({ name: 'admin', params: { tab: to.params.tab || 'general' } }) },
] satisfies RouteRecordRaw[]
