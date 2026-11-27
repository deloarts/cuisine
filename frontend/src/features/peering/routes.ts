import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    // The invitation link another administrator received. Opened in a
    // browser it explains where to paste it; the instance that accepts the
    // invitation reads the code itself.
    path: '/peering/accept',
    name: 'peering-accept',
    component: () => import('@/features/peering/views/PeeringAcceptView.vue'),
    meta: { layout: 'public', requiresAuth: false, title: 'peering.accept.title' },
  },
] satisfies RouteRecordRaw[]
