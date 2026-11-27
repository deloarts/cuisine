<script setup lang="ts">
/**
 * The consent page of Cuisine's OAuth server, which apps such as ChatGPT or
 * claude.ai open as their authorization endpoint. The person is signed in
 * with their normal session (the router's guard sends them through the
 * login first), sees which app asks, where it returns to and what it may
 * do, and allows or declines. Either way the browser then leaves for the
 * address the backend answers, which is always the app's registered
 * redirect URI.
 *
 * An unknown app or an address the app did not register is shown here and
 * never followed. A request broken in another way goes straight back to the
 * app with the error, as OAuth asks.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { errorCode, errorMessage } from '@/core/utils/errors'
import { grantConsent } from '@/features/account/api/account'
import {
  decideAuthorization,
  inspectAuthorization,
  type AuthorizationPrompt,
  type AuthorizationRequest,
} from '@/features/oauth/api/oauth'
import { authorizationRequest, initialChoice, isFixed } from '@/features/oauth/authorize'
import EmptyState from '@/shared/components/EmptyState.vue'
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, te } = useI18n()
const route = useRoute()

const request = computed<AuthorizationRequest | null>(() => authorizationRequest(route.query))
const prompt = ref<AuthorizationPrompt | null>(null)
const chosen = ref<string[]>([])
const problem = ref<string | null>(null)
const needsConsent = ref(false)
const busy = ref(false)
// Set once the browser is on its way back to the app, so nothing can be
// clicked twice.
const leaving = ref(false)

function scopeKey(permission: string): string {
  return permission.replace(':', '_')
}

function describe(err: unknown): string {
  const code = errorCode(err)
  if (code && te(`oauth.errors.${code}`)) return t(`oauth.errors.${code}`)
  return errorMessage(err, t('oauth.errors.generic'))
}

function leave(target: string) {
  leaving.value = true
  window.location.assign(target)
}

async function inspect() {
  if (!request.value) {
    problem.value = t('oauth.errors.incomplete')
    return
  }
  busy.value = true
  problem.value = null
  needsConsent.value = false
  try {
    const answer = await inspectAuthorization(request.value)
    if (answer.error_redirect) {
      leave(answer.error_redirect)
      return
    }
    prompt.value = answer
    chosen.value = initialChoice(answer)
  } catch (err) {
    if (errorCode(err) === 'ConsentRequiredError') needsConsent.value = true
    else problem.value = describe(err)
  } finally {
    busy.value = false
  }
}

async function consentAndContinue() {
  busy.value = true
  try {
    await grantConsent('ai_agents')
  } catch (err) {
    problem.value = describe(err)
    busy.value = false
    return
  }
  await inspect()
}

async function decide(approve: boolean) {
  if (!request.value) return
  busy.value = true
  try {
    leave(await decideAuthorization(request.value, approve, chosen.value))
  } catch (err) {
    problem.value = describe(err)
    busy.value = false
  }
}

onMounted(() => {
  void inspect()
})
</script>

<template>
  <div class="oauth-page">
    <ContentCard v-if="problem" class="oauth-card">
      <EmptyState :message="problem" icon="mdi mdi-link-variant-off">
        <RouterLink :to="{ name: 'home' }" custom>
          <template #default="{ navigate }">
            <Button :label="t('oauth.backHome')" severity="secondary" @click="navigate" />
          </template>
        </RouterLink>
      </EmptyState>
    </ContentCard>

    <ContentCard v-else-if="needsConsent" class="oauth-card">
      <h2 class="panel-title">{{ t('oauth.consentTitle') }}</h2>
      <p>{{ t('oauth.consentText') }}</p>
      <div class="actions">
        <RouterLink :to="{ name: 'home' }" custom>
          <template #default="{ navigate }">
            <Button :label="t('common.cancel')" severity="secondary" text @click="navigate" />
          </template>
        </RouterLink>
        <Button :label="t('oauth.consentAndContinue')" :loading="busy" @click="consentAndContinue" />
      </div>
    </ContentCard>

    <ContentCard as="form" v-else-if="prompt" class="oauth-card" @submit.prevent="decide(true)">
      <div class="app-head">
        <i class="mdi mdi-robot-outline app-icon" aria-hidden="true" />
        <div>
          <h2 class="panel-title">{{ t('oauth.asks', { name: prompt.client_name }) }}</h2>
          <p class="app-host">
            {{ t('oauth.returnsTo', { host: prompt.redirect_host }) }}
          </p>
        </div>
      </div>
      <p>{{ t('oauth.intro') }}</p>

      <fieldset class="scopes">
        <legend class="field-label">{{ t('oauth.mayLabel') }}</legend>
        <div v-for="permission in prompt.offered" :key="permission" class="scope">
          <Checkbox
            v-model="chosen"
            :input-id="`scope-${scopeKey(permission)}`"
            :value="permission"
            :disabled="isFixed(permission) || busy || leaving"
          />
          <label :for="`scope-${scopeKey(permission)}`">
            <span class="scope-name">{{ t(`oauth.scopes.${scopeKey(permission)}`) }}</span>
            <small class="field-hint">{{ t(`oauth.scopeHints.${scopeKey(permission)}`) }}</small>
          </label>
        </div>
      </fieldset>

      <p class="hint">{{ t('oauth.safety') }}</p>

      <div class="actions">
        <Button
          type="button"
          :label="t('oauth.deny')"
          severity="secondary"
          :disabled="busy || leaving"
          @click="decide(false)"
        />
        <Button type="submit" :label="t('oauth.allow')" icon="mdi mdi-check" :loading="busy || leaving" />
      </div>
    </ContentCard>

    <SkeletonRegion v-else class="card oauth-card" :label="t('oauth.loading')" testid="oauth-skeleton">
      <div class="app-head">
        <Skeleton size="2rem" shape="circle" />
        <div class="oauth-skeleton-title">
          <Skeleton width="70%" height="1.25rem" />
          <Skeleton width="45%" height="0.875rem" />
        </div>
      </div>
      <SkeletonLines :lines="2" />
      <div class="scopes">
        <div v-for="n in 3" :key="n" class="scope">
          <Skeleton size="1.25rem" />
          <div class="oauth-skeleton-title">
            <Skeleton :width="n % 2 ? '40%' : '55%'" height="1rem" />
            <Skeleton width="80%" height="0.75rem" />
          </div>
        </div>
      </div>
      <div class="actions">
        <Skeleton width="6rem" height="2.5rem" />
        <Skeleton width="6rem" height="2.5rem" />
      </div>
    </SkeletonRegion>
  </div>
</template>

<style scoped lang="scss">
.oauth-page {
  display: grid;
  justify-items: center;
  padding-block: var(--space-4);
}

.oauth-card {
  display: grid;
  gap: var(--space-3);
  width: 100%;
  max-width: 34rem;
}

.app-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.app-icon {
  font-size: var(--font-size-3xl);
  color: var(--p-primary-color);
}

.app-host {
  margin: var(--space-1) 0 0;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}

.scopes {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}

.scope {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-height: 2.75rem;

  label {
    display: grid;
    gap: var(--space-1);
  }
}

.scope-name {
  font-weight: 700;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

.oauth-skeleton-title {
  display: grid;
  flex: 1;
  gap: var(--space-2);
}
</style>
