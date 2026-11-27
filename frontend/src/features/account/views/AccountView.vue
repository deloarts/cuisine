<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import PageHeader from '@/shared/components/PageHeader.vue'
import AccountActivityTab from '@/features/account/components/AccountActivityTab.vue'
import AccountDataTab from '@/features/account/components/AccountDataTab.vue'
import AccountAgentsTab from '@/features/account/components/AccountAgentsTab.vue'
import AccountFoodRestrictionsTab from '@/features/account/components/AccountFoodRestrictionsTab.vue'
import AccountPrivacySection from '@/features/account/components/AccountPrivacySection.vue'
import AccountProfileTab from '@/features/account/components/AccountProfileTab.vue'
import AccountSecurityTab from '@/features/account/components/AccountSecurityTab.vue'
import AccountTokensTab from '@/features/account/components/AccountTokensTab.vue'
import { Permission } from '@/core/auth/permissions'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const currentUser = useCurrentUserStore()
const canUseTokens = computed(() => currentUser.hasPermission(Permission.WRITE_PAT))
const publicInfo = usePublicInfoStore()
// The AI agents tab needs the permission and the instance's agent feature.
const canUseAgents = computed(
  () => currentUser.hasPermission(Permission.USE_MCP) && publicInfo.info?.features.agents !== false,
)

// The tabs share the card's one scrolling area, so a newly opened tab starts
// at its top instead of where the previous one was left.
const tab = ref<string | number>('profile')
const card = ref<{ $el: HTMLElement } | null>(null)
watch(tab, () => {
  void nextTick(() => card.value?.$el.querySelector('.account-panels')?.scrollTo({ top: 0 }))
})
</script>

<template>
  <section class="account">
    <PageHeader :title="t('nav.account')" />
    <ContentCard ref="card" class="account-card">
      <Tabs v-model:value="tab" scrollable class="account-tabs">
        <TabList class="card-tabs">
          <Tab value="profile">{{ t('account.tabs.profile') }}</Tab>
          <Tab value="food">{{ t('foodRestrictions.tab') }}</Tab>
          <Tab value="security">{{ t('account.tabs.security') }}</Tab>
          <Tab v-if="canUseTokens" value="tokens">{{ t('account.tabs.tokens') }}</Tab>
          <Tab v-if="canUseAgents" value="agents">{{ t('consents.agents.tab') }}</Tab>
          <Tab value="activity">{{ t('account.tabs.activity') }}</Tab>
          <Tab value="data">{{ t('accountData.tab') }}</Tab>
        </TabList>
        <TabPanels class="account-panels">
          <TabPanel value="profile" class="profile-panel">
            <AccountProfileTab />
            <AccountPrivacySection />
          </TabPanel>
          <TabPanel value="food"><AccountFoodRestrictionsTab /></TabPanel>
          <TabPanel value="security"><AccountSecurityTab /></TabPanel>
          <TabPanel v-if="canUseTokens" value="tokens"><AccountTokensTab /></TabPanel>
          <TabPanel v-if="canUseAgents" value="agents"><AccountAgentsTab /></TabPanel>
          <TabPanel value="activity"><AccountActivityTab /></TabPanel>
          <TabPanel value="data"><AccountDataTab /></TabPanel>
        </TabPanels>
      </Tabs>
    </ContentCard>
  </section>
</template>


<style scoped lang="scss">
// The page fills the screen below its header on every size: the card runs
// down to the bottom, its tab bar stays in view, and only the open tab
// scrolls inside the card.
.account {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}

.account-card {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
  padding-bottom: 0;
}

.account-tabs {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}

.account-panels {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.profile-panel {
  display: grid;
  gap: var(--space-5);
}
</style>
