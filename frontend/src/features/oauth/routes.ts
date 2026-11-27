import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    // The authorization endpoint of Cuisine's OAuth server. It needs a
    // session, so the guard sends a visitor to the login first and back here
    // with the full query afterwards.
    path: '/oauth/authorize',
    name: 'oauthAuthorize',
    component: () => import('@/features/oauth/views/OAuthAuthorizeView.vue'),
    meta: { title: 'oauth.title' },
  },
] satisfies RouteRecordRaw[]
