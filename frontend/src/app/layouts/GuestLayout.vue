<script setup lang="ts">
/**
 * The shell of the public recipe pages for visitors who are not signed in:
 * the instance's wordmark linking to the public recipes, a way to sign in,
 * the page in the usual content width and the legal links at the foot. It
 * has none of the app shell's features that need a session, sets no cookie
 * and carries the robots meta tag the administrator's search engine switch
 * asks for.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import LegalLinks from '@/shared/components/legal/LegalLinks.vue'
import { useRobotsMeta } from '@/shared/composables/useRobotsMeta'

const { t } = useI18n()
const publicInfo = usePublicInfoStore()

const instanceName = computed(() => publicInfo.info?.instance_name ?? 'Cuisine')
useRobotsMeta(computed(() => publicInfo.info?.index_public_recipes ?? false))
</script>

<template>
  <div class="guest-layout">
    <header class="guest-header">
      <RouterLink :to="{ name: 'public-recipes' }" class="guest-brand">
        <span class="guest-brand-name">{{ instanceName }}</span>
      </RouterLink>
      <RouterLink :to="{ name: 'login' }" class="guest-sign-in">
        <span class="mdi mdi-login" aria-hidden="true" />
        {{ t('guest.signIn') }}
      </RouterLink>
    </header>
    <main class="guest-main">
      <div class="guest-frame">
        <RouterView />
      </div>
    </main>
    <footer class="guest-footer">
      <LegalLinks />
    </footer>
  </div>
</template>

<style scoped lang="scss">
.guest-layout {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
  background: var(--p-surface-50);
}

.p-dark .guest-layout {
  background: var(--p-surface-950);
}

.guest-header {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: var(--header-height);
  padding: 0 var(--space-3);
  padding-top: env(safe-area-inset-top);
  color: var(--header-fg);
  background-color: var(--p-primary-500);
}

.guest-brand,
.guest-sign-in {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  color: var(--header-fg);
  text-decoration: none;
}

.guest-brand-name {
  font-family: var(--font-brand);
  font-size: var(--font-size-2xl);
  line-height: 1;
}

.guest-sign-in {
  padding: 0 var(--space-3);
  border-radius: 999px;
  font-weight: 700;

  &:focus-visible {
    outline: 2px solid var(--header-fg);
    outline-offset: 2px;
  }
}

@media (hover: hover) {
  .guest-sign-in:hover {
    background-color: var(--on-accent-hover);
  }
}

.guest-main {
  flex: 1 0 auto;
  padding: var(--space-3);
}

.guest-frame {
  width: 100%;
  max-width: var(--page-width);
  margin: 0 auto;
}

.guest-footer {
  flex: none;
  padding: var(--space-2) var(--space-3);
  padding-bottom: calc(var(--space-2) + env(safe-area-inset-bottom));
  color: var(--p-text-muted-color);
}

@media (min-width: $bp-sm) {
  .guest-main {
    padding: var(--space-5) var(--space-6);
  }

  .guest-brand-name {
    font-size: var(--font-brand-size);
  }
}

// The header and footer have no place on paper; the page decides what it
// prints.
@media print {
  .guest-header,
  .guest-footer {
    display: none;
  }

  .guest-layout {
    position: static;
    overflow: visible;
    background: none;
  }
}
</style>
