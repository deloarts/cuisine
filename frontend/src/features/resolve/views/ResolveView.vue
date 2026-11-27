<script setup lang="ts">
/**
 * Opens a link by public id (`/r/<public id>`), the form that QR codes on
 * printed recipes, mails and agents use. It asks the backend's resolver what
 * the id opens and replaces itself with that page, so the back button skips
 * it. An id the reader may not open answers 404 like an unknown one, and the
 * page says the link leads nowhere.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { errorStatus } from '@/core/utils/errors'
import { resolvePublicId } from '@/features/resolve/api/resolve'
import EmptyState from '@/shared/components/EmptyState.vue'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const problem = ref<'missing' | 'error' | null>(null)

// Only a path inside this app is followed, never another origin.
function isAppPath(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//')
}

async function open(publicId: string) {
  problem.value = null
  try {
    const found = await resolvePublicId(publicId)
    if (!isAppPath(found.route)) {
      problem.value = 'missing'
      return
    }
    await router.replace(found.route)
  } catch (err) {
    problem.value = errorStatus(err) === 404 ? 'missing' : 'error'
  }
}

watch(
  () => route.params.publicId,
  (publicId) => {
    if (typeof publicId === 'string') void open(publicId)
  },
  { immediate: true },
)
</script>

<template>
  <ContentCard v-if="problem">
    <EmptyState
      :message="problem === 'missing' ? t('resolve.notFound') : t('resolve.failed')"
      icon="mdi mdi-link-variant-off"
    >
      <RouterLink :to="{ name: 'home' }" custom>
        <template #default="{ navigate }">
          <Button :label="t('resolve.backHome')" severity="secondary" @click="navigate" />
        </template>
      </RouterLink>
    </EmptyState>
  </ContentCard>
  <div v-else class="resolve-loading" role="status">
    <ProgressSpinner :aria-label="t('resolve.opening')" />
  </div>
</template>

<style scoped lang="scss">
.resolve-loading {
  display: grid;
  place-items: center;
  padding: var(--space-6);
}
</style>
