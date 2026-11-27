<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import { authApi } from '@/core/api/auth'
import { useSessionCountdown } from '@/core/composables/useSessionCountdown'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { useLayoutStore } from '@/core/stores/layoutStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import UserAvatar from '@/shared/components/UserAvatar.vue'

const { t } = useI18n()
const router = useRouter()
const currentUser = useCurrentUserStore()
const layoutStore = useLayoutStore()
const publicInfo = usePublicInfoStore()
const countdown = useSessionCountdown()

const menu = ref<{ toggle: (event: Event) => void } | null>(null)

const instanceName = computed(() => publicInfo.info?.instance_name ?? 'Cuisine')

async function logout() {
  try {
    await authApi.post('/logout')
  } finally {
    currentUser.clear()
    await router.push({ name: 'login' })
  }
}

const items = computed<MenuItem[]>(() => [
  { label: currentUser.user?.display_name ?? '', disabled: true },
  { separator: true },
  {
    label: t('nav.account'),
    icon: 'mdi mdi-account-cog-outline',
    command: () => void router.push({ name: 'account' }),
  },
  { label: t('nav.logout'), icon: 'mdi mdi-logout', command: () => void logout() },
])
</script>

<template>
  <div class="header">
    <div class="header-left">
      <Button
        icon="mdi mdi-menu"
        text
        rounded
        class="header-button sidebar-toggle"
        :aria-label="t('nav.toggleSidebar')"
        @click="layoutStore.toggleSidebarWide()"
      />
      <RouterLink to="/" class="brand">
        <span class="brand-name">{{ instanceName }}</span>
      </RouterLink>
    </div>

    <div class="header-right">
      <button
        type="button"
        class="avatar-button"
        :aria-label="t('nav.userMenu')"
        aria-haspopup="true"
        @click="menu?.toggle($event)"
      >
        <UserAvatar
          class="avatar"
          :name="currentUser.user?.display_name ?? ''"
          :avatar-id="currentUser.user?.avatar_id"
        />
      </button>
      <Menu ref="menu" :model="items" popup />
      <span
        v-if="countdown.isActive.value"
        v-tooltip.bottom="t('nav.sessionCountdown')"
        class="session-countdown"
        :class="{ warning: countdown.isWarning.value }"
        role="timer"
        aria-live="off"
      >{{ countdown.label }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--space-2);
  // --header-fg, not --p-primary-contrast-color: the contrast colour turns
  // dark under .p-dark and would flash the wordmark black.
  color: var(--header-fg);
  background-color: var(--p-primary-500);
  user-select: none;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-button {
  --p-button-text-primary-color: var(--header-fg);
  --p-button-text-primary-hover-background: var(--on-accent-hover);
  --p-button-text-primary-active-background: var(--on-accent-hover);
}

.brand {
  display: flex;
  align-items: center;
  // Without the rail toggle in front of it on a phone, the wordmark keeps a
  // little room from the screen's edge.
  padding-inline-start: var(--space-2);
  color: var(--header-fg);
  text-decoration: none;
}

// On a phone the bottom nav's More opens the navigation, so the rail toggle
// only appears from a tablet up, and the wordmark starts slightly smaller as
// the only brand on screen.
.sidebar-toggle {
  display: none;
}

.brand-name {
  font-family: var(--font-brand);
  font-size: var(--font-size-2xl);
  line-height: 1;
  letter-spacing: 0.01em;
}

.avatar-button {
  display: flex;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  border-radius: 50%;

  &:focus-visible {
    outline: 2px solid var(--header-fg);
    outline-offset: 2px;
  }
}

.avatar {
  --avatar-size: 2.2rem;
  --avatar-background: var(--p-primary-700);
  --avatar-color: var(--header-fg);
}

.session-countdown {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-head);
  font-size: var(--font-size-sm);
  font-variant-numeric: tabular-nums;
  color: var(--header-fg);
  background-color: var(--on-accent-hover);
  border-radius: 999px;
}

// The last minute turns red. The colour holds in both themes, since the
// header keeps its primary background in dark mode too.
.session-countdown.warning {
  background-color: var(--p-red-600);
}

@media (min-width: $bp-sm) {
  .sidebar-toggle {
    display: inline-flex;
  }

  .brand {
    padding-inline-start: 0;
  }

  .brand-name {
    font-size: var(--font-brand-size);
  }
}
</style>
