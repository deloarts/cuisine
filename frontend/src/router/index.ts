import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouteRecordRaw,
} from 'vue-router'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'

declare module 'vue-router' {
  interface RouteMeta {
    // 'auth' renders the sign-in shell; 'fullscreen' renders the page alone,
    // without header and navigation (cook mode); 'public' renders in the app
    // shell when signed in and on a plain page otherwise (the legal pages);
    // 'guest' renders the shell of the public recipe pages for visitors who
    // are not signed in. Without it, the page renders in the app shell.
    layout?: 'auth' | 'fullscreen' | 'public' | 'guest'
    // False for the public pages; every other page needs a session.
    requiresAuth?: boolean
    // Any one of these permissions opens the page.
    permissions?: string[]
    // An i18n key for the browser title.
    title?: string
  }
}

// Every feature registers its pages in its own `routes.ts`, so features are
// added without editing this file. The catch-all stays last.
const featureRoutes = import.meta.glob<RouteRecordRaw[]>('../features/*/routes.ts', {
  eager: true,
  import: 'default',
})

export const routes: RouteRecordRaw[] = [
  ...Object.values(featureRoutes).flat(),
  { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/** Where a guard sends a request it refuses. */
export function guard(to: RouteLocationNormalized) {
  const store = useCurrentUserStore()
  if (to.meta.requiresAuth === false) {
    // A signed-in user has nothing to do on the login page.
    if (to.name === 'login' && store.isSignedIn) return { name: 'home' }
    return true
  }
  if (!store.isSignedIn) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  const needed = to.meta.permissions
  if (needed && !needed.some((p) => store.hasPermission(p))) return { name: 'home' }
  return true
}

router.beforeEach(async (to) => {
  const store = useCurrentUserStore()
  if (!store.loaded) await store.refresh()
  return guard(to)
})

export default router
