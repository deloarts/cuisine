<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useNavigation, type NavEntry } from '@/app/navigation'
import { useLayoutStore } from '@/core/stores/layoutStore'

// In the phone overlay the labels always show, so no tooltip is needed.
const props = defineProps<{ overlay?: boolean }>()

const { t } = useI18n()
const layoutStore = useLayoutStore()
const { main, kitchen, admin } = useNavigation()

const showLabels = computed(() => props.overlay || layoutStore.isSidebarWide)

const groups = computed(() =>
  [
    { key: 'main', title: '', entries: main.value },
    { key: 'kitchen', title: t('nav.kitchen'), entries: kitchen.value },
  ].filter((group) => group.entries.length),
)

function tooltip(entry: NavEntry) {
  return showLabels.value ? undefined : entry.label
}
</script>

<template>
  <nav class="sidebar" :class="{ 'show-labels': showLabels }" :aria-label="t('nav.main')">
    <div class="nav-groups">
      <div v-for="group in groups" :key="group.key" class="nav-group">
        <p v-if="group.title" class="nav-group-title">{{ group.title }}</p>
        <hr v-if="group.title" class="nav-divider" />
        <ul class="nav-list">
          <li v-for="entry in group.entries" :key="entry.to">
            <RouterLink
              v-tooltip.right="tooltip(entry)"
              :to="entry.to"
              class="nav-link"
              :exact-active-class="entry.exact ? 'is-active' : undefined"
              :active-class="entry.exact ? undefined : 'is-active'"
            >
              <span class="mdi nav-icon" :class="entry.icon" aria-hidden="true" />
              <span class="nav-label">{{ entry.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </div>

    <ul v-if="admin" class="nav-list nav-footer">
      <li>
        <RouterLink
          v-tooltip.right="tooltip(admin)"
          :to="admin.to"
          class="nav-link"
          active-class="is-active"
        >
          <span class="mdi nav-icon" :class="admin.icon" aria-hidden="true" />
          <span class="nav-label">{{ admin.label }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<style scoped lang="scss">
.sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 100%;
  padding: var(--space-3) var(--space-2);
}

.nav-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

// The group caption only reads when the labels show; the narrow rail keeps
// the divider alone.
.nav-group-title {
  display: none;
  padding: 0 var(--space-2);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.show-labels .nav-group-title {
  display: block;
}

.show-labels .nav-divider {
  display: none;
}

.nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  border-radius: var(--p-border-radius-lg);
  color: var(--p-text-muted-color);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;

  &:hover {
    background: var(--p-content-hover-background);
    color: var(--p-text-color);
  }

  &.is-active {
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
    font-weight: 700;
  }
}

.nav-icon {
  flex: 0 0 auto;
  font-size: var(--font-size-xl);
  line-height: 1;
}

.nav-label {
  font-size: var(--font-size-md);
}

.nav-divider {
  border: none;
  height: 1px;
  background: var(--p-content-border-color);
  margin: 0 var(--space-1) var(--space-1);
}
</style>
