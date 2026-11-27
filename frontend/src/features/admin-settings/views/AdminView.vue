<script setup lang="ts">
/**
 * The admin area: one route, `/admin/:tab?`, with the tabs right under the
 * app header and the active tab in the URL, so a tab can be linked and the
 * back button walks through them. Each tab stacks its sections as cards.
 *
 * The tab bar is teleported into the layout's page bar, so it spans the
 * whole content area from the sidebar to the window's edge and stays at the
 * top while the sections scroll. The section components of every visible
 * tab are fetched when the area opens, so a tab switch shows its sections at
 * once and only their values wait for the server.
 */
import { computed, inject, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { preloadSections, visibleTabs } from '@/features/admin-settings/adminTabs'
import { TOTP_GUARDED_PERMISSIONS } from '@/core/auth/permissions'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const currentUser = useCurrentUserStore()
const publicInfo = usePublicInfoStore()

// AppLayout provides the page bar; outside it (in a test) the tabs stay in place.
const hasPageBar = inject('pageBar', false)

const tabs = computed(() =>
  visibleTabs(
    // The settings tabs wait for two-factor authentication, as the backend does.
    (p) => currentUser.hasPermission(p) && !(currentUser.settingsNeedTotp && TOTP_GUARDED_PERMISSIONS.includes(p)),
    (feature) => Boolean((publicInfo.info?.features as Record<string, boolean> | undefined)?.[feature]),
  ),
)
const requested = computed(() => (typeof route.params.tab === 'string' ? route.params.tab : ''))
const active = computed({
  get: () => (tabs.value.some((tab) => tab.value === requested.value) ? requested.value : (tabs.value[0]?.value ?? '')),
  set: (value: string) => void router.push({ name: 'admin', params: { tab: value } }),
})

// An unknown or forbidden tab in the URL becomes the first one the user may see.
watch(
  [requested, tabs],
  () => {
    if (active.value && requested.value !== active.value) {
      void router.replace({ name: 'admin', params: { tab: active.value } })
    }
  },
  { immediate: true },
)

onMounted(() => preloadSections(tabs.value))
</script>

<template>
  <section class="admin">
    <h1 class="visually-hidden">{{ t('nav.admin') }}</h1>
    <Message v-if="currentUser.settingsNeedTotp" severity="warn" :closable="false" class="totp-notice">
      {{ t('adminArea.settingsNeedTotp') }}
      <RouterLink :to="{ name: 'account' }">{{ t('adminArea.settingsNeedTotpLink') }}</RouterLink>
    </Message>
    <Tabs v-model:value="active" scrollable>
      <Teleport to="#page-bar" defer :disabled="!hasPageBar">
        <TabList class="admin-tabbar">
          <Tab v-for="tab in tabs" :key="tab.value" :value="tab.value">
            <i class="mdi tab-icon" :class="tab.icon" aria-hidden="true" />
            {{ t(`adminArea.tabs.${tab.value}`) }}
          </Tab>
        </TabList>
      </Teleport>
      <TabPanels class="admin-panels">
        <TabPanel v-for="tab in tabs" :key="tab.value" :value="tab.value">
          <div v-if="active === tab.value" class="admin-sections">
            <ContentCard v-for="section in tab.sections" :key="section.key" class="admin-section">
              <h2 v-if="section.titled" class="panel-title">{{ t(`adminArea.sections.${section.key}`) }}</h2>
              <component :is="section.component" v-bind="section.props ?? {}" />
            </ContentCard>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </section>
</template>

<style scoped lang="scss">
// The bar reaches past the content area's padding (named by AppLayout) to
// the header above and the edges on both sides, and keeps a padding's
// distance to the sections below. A sticky offset counts from inside the
// scroll area's padding, so the bar sticks at minus that padding to stay
// flush under the header.
.admin-tabbar {
  position: sticky;
  top: calc(-1 * var(--shell-pad-y));
  z-index: 1;
  margin: calc(-1 * var(--shell-pad-y)) calc(-1 * var(--shell-pad-x)) var(--shell-pad-y);
}

.tab-icon {
  margin-right: var(--space-1);
}

.admin-sections {
  display: grid;
  gap: var(--space-3);
}

.admin-section {
  display: grid;
  gap: var(--space-3);
}
</style>
