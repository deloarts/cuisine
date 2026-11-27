<script setup lang="ts">
/**
 * Where an invitation link lands when someone opens it in a browser. The
 * link is meant for the other instance's admin area, so the page explains
 * where to paste it and shows it with a copy button. It sends the code
 * nowhere: only the accepting instance's server uses it.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import PageHeader from '@/shared/components/PageHeader.vue'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const route = useRoute()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const publicInfo = usePublicInfoStore()

const link = computed(() => `${window.location.origin}${route.fullPath}`)
const instance = computed(() => publicInfo.info?.instance_name || t('peering.accept.thisInstance'))

async function copy() {
  try {
    await navigator.clipboard.writeText(link.value)
    toast.success(t('peering.accept.copied'))
  } catch (err) {
    toast.error(err)
  }
}
</script>

<template>
  <section class="accept-page">
    <PageHeader :title="t('peering.accept.title')" />
    <ContentCard class="accept-card">
      <p>{{ t('peering.accept.intro', { instance }) }}</p>
      <p>{{ t('peering.accept.steps') }}</p>
      <div class="field">
        <label for="peering-invitation-link">{{ t('peering.accept.linkLabel') }}</label>
        <div class="link-row">
          <InputText id="peering-invitation-link" :model-value="link" readonly fluid />
          <Button :label="t('common.copy')" icon="mdi mdi-content-copy" @click="copy" />
        </div>
        <small class="field-hint">{{ t('peering.accept.once') }}</small>
      </div>
    </ContentCard>
    <RouterLink v-if="currentUser.isSignedIn" :to="{ name: 'home' }" class="back">
      <i class="mdi mdi-arrow-left" aria-hidden="true" /> {{ t('peering.accept.toApp') }}
    </RouterLink>
    <RouterLink v-else :to="{ name: 'login' }" class="back">
      <i class="mdi mdi-arrow-left" aria-hidden="true" /> {{ t('peering.accept.toLogin') }}
    </RouterLink>
  </section>
</template>

<style scoped lang="scss">
.accept-page {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.accept-card {
  display: grid;
  gap: var(--space-3);

  p {
    margin: 0;
  }
}

.field {
  display: grid;
  gap: var(--space-1);
}

.link-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
}

.back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  color: var(--p-primary-color);
}
</style>
