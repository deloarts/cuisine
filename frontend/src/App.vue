<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { START_LOCATION, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppLayout from '@/app/layouts/AppLayout.vue'
import AppPrivacyGate from '@/app/layouts/AppPrivacyGate.vue'
import AuthLayout from '@/app/layouts/AuthLayout.vue'
import GuestLayout from '@/app/layouts/GuestLayout.vue'
import { privacyPending } from '@/core/privacy/privacyGate'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { useLayoutStore } from '@/core/stores/layoutStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const layoutStore = useLayoutStore()
const publicInfo = usePublicInfoStore()
const currentUser = useCurrentUserStore()

// Nothing renders until the first navigation resolved, so the app shell
// never flashes up on the way to the login page.
const firstRouteResolved = computed(() => router.currentRoute.value !== START_LOCATION)
const layout = computed(() => route.meta.layout ?? 'app')
// Until the current privacy statement is acknowledged the backend refuses
// almost every request, so the statement takes the place of the page.
const gated = computed(
  () => layout.value !== 'auth' && layout.value !== 'guest' && privacyPending(currentUser.user),
)

// The browser title: the page, then the instance name.
watch(
  [() => route.meta.title, () => publicInfo.info?.instance_name],
  ([title, instance]) => {
    const name = instance ?? 'Cuisine'
    document.title = title ? `${t(title)} · ${name}` : name
  },
  { immediate: true },
)

// A session that ended mid-visit lands on the login page.
watch(
  () => currentUser.expired,
  (expired) => {
    if (expired && route.meta.requiresAuth !== false) {
      void router.push({ name: 'login', query: { redirect: route.fullPath, expired: '1' } })
    }
  },
)

onMounted(() => {
  layoutStore.initDefaultTheme()
  void publicInfo.fetch()
})
</script>

<template>
  <Toast />
  <ConfirmDialog />

  <template v-if="firstRouteResolved">
    <AuthLayout v-if="layout === 'auth'" />
    <GuestLayout v-else-if="layout === 'guest'" />
    <AppPrivacyGate v-else-if="gated" />
    <main v-else-if="layout === 'fullscreen'" class="fullscreen-page">
      <RouterView />
    </main>
    <main v-else-if="layout === 'public' && !currentUser.isSignedIn" class="public-page">
      <div class="public-frame">
        <RouterView />
      </div>
    </main>
    <AppLayout v-else />
  </template>
</template>

<style scoped lang="scss">
// A page without the shell, such as cook mode, owns the whole viewport and
// scrolls on its own.
.fullscreen-page {
  position: fixed;
  inset: 0;
  overflow: auto;
  background: var(--p-content-background);
}

// A public page before sign-in, such as the imprint: no shell, the same
// content width as inside it.
.public-page {
  position: fixed;
  inset: 0;
  overflow: auto;
  padding: var(--space-3);
  background: var(--p-surface-50);
}

.public-frame {
  width: 100%;
  max-width: var(--page-width);
  margin: 0 auto;
}

.p-dark .public-page {
  background: var(--p-surface-950);
}

@media (min-width: $bp-sm) {
  .public-page {
    padding: var(--space-5) var(--space-6);
  }
}
</style>
