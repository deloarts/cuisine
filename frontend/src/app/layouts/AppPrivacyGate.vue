<script setup lang="ts">
/**
 * The blocking privacy statement. It replaces the app while the signed-in
 * user has not acknowledged the current version, names the instance's
 * privacy mode in plain words as the administrator's decision, and offers
 * only two ways on: accept, which records the version, or decline, which
 * ends the session.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'
import { useToast } from 'openvue/usetoast'

import LegalText from '@/shared/components/legal/LegalText.vue'
import LegalTextSkeleton from '@/shared/components/legal/LegalTextSkeleton.vue'
import { acknowledgePrivacy, declinePrivacy, getLegalPage, type LegalPage } from '@/shared/api/legal'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { modeOfSnapshot } from '@/shared/cookbook/privacyMode'
import { useAppToast } from '@/core/composables/useAppToast'
import { isStalePrivacyVersion } from '@/core/privacy/privacyGate'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t, locale } = useI18n()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const appToast = useAppToast()
const currentUser = useCurrentUserStore()

const page = ref<LegalPage | null>(null)
const loading = ref(false)
const failed = ref(false)
const busy = ref<'accept' | 'decline' | null>(null)

const snapshot = computed(() => currentUser.user?.privacy_mode ?? null)
const mode = computed(() => (snapshot.value ? modeOfSnapshot(snapshot.value) : null))
const defaultVisibility = computed(() =>
  snapshot.value ? t(`privacyMode.visibility.${snapshot.value.default_visibility}`) : '',
)
// Someone who accepted an earlier version sees why the statement is back.
const seenBefore = computed(() => currentUser.user?.privacy_acknowledged_version != null)

async function load() {
  loading.value = true
  failed.value = false
  try {
    page.value = await getLegalPage('privacy', contentLocaleOf(locale.value))
  } catch {
    page.value = null
    failed.value = true
  } finally {
    loading.value = false
  }
}

async function accept() {
  if (!page.value) return
  busy.value = 'accept'
  try {
    await acknowledgePrivacy(page.value.version)
    await currentUser.refresh()
  } catch (err) {
    if (isStalePrivacyVersion(err)) {
      toast.add({ severity: 'warn', summary: t('privacyGate.stale'), life: 6000 })
      await load()
    } else {
      appToast.error(err)
    }
  } finally {
    busy.value = null
  }
}

async function decline() {
  busy.value = 'decline'
  try {
    await declinePrivacy()
    currentUser.clear()
    await router.push({ name: 'login' })
  } catch (err) {
    appToast.error(err)
  } finally {
    busy.value = null
  }
}

function askDecline() {
  confirm.require({
    header: t('privacyGate.decline'),
    message: t('privacyGate.declineConfirm'),
    acceptProps: { label: t('privacyGate.decline'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void decline(),
  })
}

watch(locale, () => void load())
onMounted(() => void load())
</script>

<template>
  <div class="privacy-gate">
    <Dialog
      :visible="true"
      modal
      :closable="false"
      :close-on-escape="false"
      :draggable="false"
      :header="t('privacyGate.title')"
      class="privacy-dialog"
    >
      <div class="gate-body">
        <p class="intro">{{ seenBefore ? t('privacyGate.newVersion') : t('privacyGate.intro') }}</p>

        <section v-if="mode" class="mode" aria-labelledby="privacy-mode-title">
          <h3 id="privacy-mode-title" class="mode-title">
            <i class="mdi mdi-shield-account-outline" aria-hidden="true" />
            {{ t('privacyGate.modeTitle') }}
          </h3>
          <p class="mode-text">
            <strong>{{ t(`privacyMode.modes.${mode}`) }}</strong>
            {{ t(`privacyMode.modeText.${mode}`, { visibility: defaultVisibility }) }}
          </p>
          <p class="mode-admin">{{ t('privacyGate.adminDecision') }}</p>
        </section>

        <div v-if="loading" class="statement">
          <LegalTextSkeleton :dated="false" :sections="2" />
        </div>
        <div v-else-if="failed" class="failed">
          <Message severity="error" :closable="false">{{ t('privacyGate.loadFailed') }}</Message>
          <Button :label="t('privacyGate.retry')" icon="mdi mdi-refresh" text @click="load" />
        </div>
        <div v-else-if="page" class="statement" tabindex="0" :aria-label="t('privacyGate.title')">
          <LegalText :text="page.body" />
        </div>
      </div>

      <template #footer>
        <div class="gate-actions">
          <Button
            :label="t('privacyGate.decline')"
            icon="mdi mdi-logout"
            severity="danger"
            text
            :loading="busy === 'decline'"
            :disabled="busy !== null"
            @click="askDecline"
          />
          <Button
            :label="t('privacyGate.accept')"
            icon="mdi mdi-check"
            :loading="busy === 'accept'"
            :disabled="!page || busy !== null"
            @click="accept"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
.privacy-gate {
  position: fixed;
  inset: 0;
  background: var(--p-surface-100);
}

.p-dark .privacy-gate {
  background: var(--p-surface-950);
}

.privacy-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.gate-body {
  display: grid;
  gap: var(--space-4);
}

.intro {
  margin: 0;
}

.mode {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-left: 4px solid var(--p-primary-color);
  border-radius: var(--p-border-radius-md);
  background: var(--p-highlight-background);
}

.mode-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-lg);
}

.mode-text,
.mode-admin {
  margin: 0;
}

.mode-admin {
  font-size: var(--font-size-sm);
}

.statement {
  max-height: 50vh;
  overflow: auto;
  padding-right: var(--space-2);
}

.failed {
  display: grid;
  justify-items: start;
  gap: var(--space-2);
}

.gate-actions {
  display: flex;
  flex-wrap: wrap-reverse;
  justify-content: flex-end;
  gap: var(--space-2);
  width: 100%;
}
</style>
