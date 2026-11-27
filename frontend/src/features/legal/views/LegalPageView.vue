<script setup lang="ts">
/**
 * The published imprint or privacy statement, readable without a session.
 * Signed in, it renders inside the app shell; otherwise on a plain page with
 * a way back to the sign-in.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import LegalText from '@/shared/components/legal/LegalText.vue'
import LegalTextSkeleton from '@/shared/components/legal/LegalTextSkeleton.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { getLegalPage, type LegalPage, type LegalPageKind } from '@/shared/api/legal'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import { formatDate } from '@/core/utils/dates'
import { errorStatus } from '@/core/utils/errors'
import ContentCard from '@/shared/components/ContentCard.vue'

const props = defineProps<{ kind: LegalPageKind }>()

const { t, locale } = useI18n()
const currentUser = useCurrentUserStore()
const publicInfo = usePublicInfoStore()

const page = ref<LegalPage | null>(null)
const loading = ref(true)
const missing = ref(false)
const failed = ref(false)

const title = computed(() => t(`legal.${props.kind}`))

async function load() {
  loading.value = true
  missing.value = false
  failed.value = false
  try {
    page.value = await getLegalPage(props.kind, contentLocaleOf(locale.value))
  } catch (err) {
    page.value = null
    if (errorStatus(err) === 404) missing.value = true
    else failed.value = true
  } finally {
    loading.value = false
  }
}

// The route serves two pages, so the browser title comes from here rather
// than from the route's meta.
watch(
  [title, () => publicInfo.info?.instance_name],
  ([value, instance]) => {
    document.title = `${value} · ${instance ?? 'Cuisine'}`
  },
  { immediate: true, flush: 'post' },
)
watch([() => props.kind, locale], () => void load(), { immediate: true })
</script>

<template>
  <section class="legal-page">
    <PageHeader :title="title" />
    <ContentCard>
      <LegalTextSkeleton v-if="loading" />
      <p v-else-if="missing" class="hint">{{ t('legal.notPublished') }}</p>
      <Message v-else-if="failed" severity="error" :closable="false">{{ t('common.error') }}</Message>
      <template v-else-if="page">
        <p class="hint">{{ t('legal.published', { date: formatDate(page.published_at) }) }}</p>
        <LegalText :text="page.body" />
      </template>
    </ContentCard>
    <RouterLink v-if="currentUser.isSignedIn" :to="{ name: 'home' }" class="back">
      <i class="mdi mdi-arrow-left" aria-hidden="true" /> {{ t('legal.toApp') }}
    </RouterLink>
    <RouterLink v-else :to="{ name: 'login' }" class="back">
      <i class="mdi mdi-arrow-left" aria-hidden="true" /> {{ t('legal.toLogin') }}
    </RouterLink>
  </section>
</template>

<style scoped lang="scss">
.legal-page {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  color: var(--p-primary-color);
}
</style>
