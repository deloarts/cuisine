<script setup lang="ts">
/**
 * The phone's main navigation: the everyday places one tap away. More opens
 * the sidebar as an overlay with everything else.
 */
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { useNavigation, type NavEntry } from '@/app/navigation'

const moreOpen = defineModel<boolean>('moreOpen', { required: true })

const { t } = useI18n()
const route = useRoute()
const { bottom } = useNavigation()

function isActive(entry: NavEntry): boolean {
  if (moreOpen.value) return false
  return entry.exact ? route.path === entry.to : route.path.startsWith(entry.to)
}
</script>

<template>
  <nav class="bottom-nav" :aria-label="t('nav.bottomNav')">
    <RouterLink
      v-for="entry in bottom"
      :key="entry.to"
      :to="entry.to"
      class="bottom-nav-item"
      :class="{ active: isActive(entry) }"
      :aria-current="isActive(entry) ? 'page' : undefined"
    >
      <i class="mdi" :class="entry.icon" aria-hidden="true" />
      <span class="bottom-nav-label">{{ entry.label }}</span>
    </RouterLink>
    <button
      type="button"
      class="bottom-nav-item"
      :class="{ active: moreOpen }"
      :aria-expanded="moreOpen"
      data-testid="bottom-nav-more"
      @click="moreOpen = !moreOpen"
    >
      <i class="mdi" :class="moreOpen ? 'mdi-close' : 'mdi-menu'" aria-hidden="true" />
      <span class="bottom-nav-label">{{ t('nav.more') }}</span>
    </button>
  </nav>
</template>

<style scoped lang="scss">
.bottom-nav {
  display: flex;
  height: 100%;
  // Keeps the entries above the home indicator of an installed app.
  padding-bottom: env(safe-area-inset-bottom, 0px);
  user-select: none;
  background-color: var(--p-content-background);
  border-top: 1px solid var(--p-content-border-color);
}

.bottom-nav-item {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-width: 0;
  padding: 0;
  cursor: pointer;
  color: var(--p-text-muted-color);
  background: transparent;
  border: none;
  border-top: 0.2rem solid transparent;
  font: inherit;
  text-decoration: none;
}

.bottom-nav-item i {
  font-size: var(--font-size-xl);
  margin: 0;
  pointer-events: none;
}

.bottom-nav-label {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: var(--font-size-xs);
}

.bottom-nav-item.active {
  color: var(--p-primary-color);
  border-top-color: var(--p-primary-500);
  font-weight: 700;
}

.bottom-nav-item:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: -2px;
}
</style>
