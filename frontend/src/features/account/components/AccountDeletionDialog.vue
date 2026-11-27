<script setup lang="ts">
/**
 * Deletes the own account for good. The dialog reads what the deletion does
 * for this user on this instance and lists it in three groups (stays online,
 * handed over, deleted), names how long the backups still hold the data,
 * offers to delete the public recipes too when the instance allows it, and
 * deletes only after a re-authentication and the typed e-mail address.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { getPasskey, passkeyPromptDismissed, passkeysSupported } from '@/features/auth/utils/webauthn'
import { deleteOwnAccount, ownDeletionImpact, passkeyChallenge } from '@/features/account/api/account'
import {
  canDeleteOwn,
  deletionBody,
  emptyForm,
  offersPublicDeletion,
  refused,
  summarise,
  type SelfDeletionForm,
  type SelfDeletionImpact,
} from '@/features/account/selfDeletion'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDate } from '@/core/utils/dates'
import { forgetRememberedAccount } from '@/features/auth/utils/rememberedAccounts'

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ download: [] }>()

const { t } = useI18n()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()

const impact = ref<SelfDeletionImpact | null>(null)
const form = ref<SelfDeletionForm>(emptyForm())
const loading = ref(false)
const deleting = ref(false)
const confirmingPasskey = ref(false)
const canUsePasskey = passkeysSupported()

const email = computed(() => currentUser.user?.email ?? '')
const summary = computed(() => (impact.value ? summarise(impact.value, form.value.deletePublic) : null))
const ready = computed(() => (impact.value ? canDeleteOwn(impact.value, form.value, email.value) : false))
const groups = computed(() =>
  summary.value
    ? [
        { key: 'staysOnline', icon: 'mdi-earth', lines: summary.value.staysOnline },
        { key: 'handedOver', icon: 'mdi-hand-heart-outline', lines: summary.value.handedOver },
        { key: 'deleted', icon: 'mdi-delete-outline', lines: summary.value.deleted },
      ].filter((g) => g.lines.length > 0)
    : [],
)

/** A date-only string as a local date, so no time zone moves it a day. */
function localDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1)
}

watch(visible, async (open) => {
  if (!open) return
  impact.value = null
  form.value = emptyForm()
  loading.value = true
  try {
    impact.value = await ownDeletionImpact()
  } catch (err) {
    toast.error(err)
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function confirmWithPasskey() {
  confirmingPasskey.value = true
  try {
    const challenge = await passkeyChallenge()
    const credential = await getPasskey(challenge.options)
    form.value = { ...form.value, passkey: { challenge_token: challenge.challenge_token, credential } }
  } catch (err) {
    if (!passkeyPromptDismissed(err)) toast.error(err)
  } finally {
    confirmingPasskey.value = false
  }
}

async function remove() {
  if (!impact.value || !ready.value) return
  deleting.value = true
  try {
    await deleteOwnAccount(deletionBody(impact.value, form.value))
    toast.success(t('accountDeletion.deleted'))
    visible.value = false
    if (currentUser.user) forgetRememberedAccount(currentUser.user.id)
    currentUser.clear()
    await router.push({ name: 'login' })
  } catch (err) {
    // A passkey assertion is single-use, so a failed attempt needs a new one.
    form.value = { ...form.value, passkey: null }
    toast.error(err)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('accountDeletion.title')" class="deletion-dialog">
    <div v-if="loading" class="hint">{{ t('accountDeletion.loading') }}</div>

    <div v-else-if="impact && refused(impact)" class="deletion">
      <Message severity="warn" :closable="false">
        {{ t(`accountDeletion.refused.${impact.refused_reason}`) }}
      </Message>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.close')" @click="visible = false" />
      </div>
    </div>

    <form v-else-if="impact && summary" class="deletion" @submit.prevent="remove">
      <Message severity="secondary" :closable="false">
        <span>{{ t('accountDeletion.downloadFirst') }}</span>
        <Button
          type="button"
          :label="t('accountData.download')"
          icon="mdi mdi-download"
          size="small"
          text
          @click="emit('download')"
        />
      </Message>

      <section v-for="group in groups" :key="group.key" class="block">
        <h3 class="block-title">
          <i class="mdi" :class="group.icon" aria-hidden="true" />
          {{ t(`accountDeletion.groups.${group.key}`) }}
        </h3>
        <ul class="facts">
          <li v-for="line in group.lines" :key="line.key">
            {{ t(`accountDeletion.lines.${line.key}`, { count: line.count }, line.count) }}
            <ul v-if="line.recipes" class="facts">
              <li v-for="recipe in line.recipes" :key="recipe.id">
                {{ t('accountDeletion.lines.handedOverTo', { title: recipe.title, owner: recipe.new_owner_name }) }}
              </li>
            </ul>
          </li>
        </ul>
      </section>

      <section class="block">
        <h3 class="block-title">
          <i class="mdi mdi-account-remove-outline" aria-hidden="true" />
          {{ t('accountDeletion.personalTitle') }}
        </h3>
        <p class="personal">{{ t('accountDeletion.personal') }}</p>
        <ul class="facts">
          <li v-if="impact.in_household">{{ t('accountDeletion.household') }}</li>
          <li>{{ t('accountDeletion.securityEvent') }}</li>
        </ul>
      </section>

      <div v-if="offersPublicDeletion(impact)" class="choice">
        <Checkbox v-model="form.deletePublic" input-id="deletion-public" binary />
        <label for="deletion-public">
          {{ t('accountDeletion.deletePublic', { count: impact.recipes_kept_online }, impact.recipes_kept_online) }}
        </label>
      </div>

      <Message v-if="impact.backup_keep_days > 0" severity="warn" :closable="false">
        {{
          t('accountDeletion.backups', {
            days: impact.backup_keep_days,
            date: formatDate(localDate(impact.backups_clear_by)),
          })
        }}
      </Message>

      <fieldset class="reauth">
        <legend class="field-label">{{ t('accountDeletion.reauthTitle') }}</legend>
        <p v-if="form.passkey" class="passkey-ok">
          <i class="mdi mdi-check-circle-outline" aria-hidden="true" /> {{ t('accountDeletion.passkeyConfirmed') }}
        </p>
        <template v-else>
          <div class="field">
            <label for="deletion-password">{{ t('accountDeletion.password') }}</label>
            <Password
              v-model="form.password"
              input-id="deletion-password"
              :feedback="false"
              toggle-mask
              autocomplete="current-password"
              fluid
            />
          </div>
          <Button
            v-if="canUsePasskey"
            type="button"
            :label="t('accountDeletion.usePasskey')"
            icon="mdi mdi-fingerprint"
            outlined
            :loading="confirmingPasskey"
            @click="confirmWithPasskey"
          />
        </template>
      </fieldset>

      <div class="field">
        <label for="deletion-email">{{ t('accountDeletion.typeEmail', { email }) }}</label>
        <InputText id="deletion-email" v-model="form.typed" autocomplete="off" spellcheck="false" fluid />
      </div>

      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button
          type="submit"
          :label="t('accountDeletion.delete')"
          icon="mdi mdi-delete-forever"
          severity="danger"
          :disabled="!ready"
          :loading="deleting"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.deletion-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.deletion {
  display: grid;
  gap: var(--space-4);
}

.block {
  display: grid;
  gap: var(--space-1);
}

.block-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-md);
}

.facts {
  margin: 0;
  padding-left: var(--space-5);
}

.personal {
  margin: 0;
}

.choice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.reauth {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}

.passkey-ok {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: var(--p-green-600);
}

.dialog-actions {
  display: flex;
  flex-wrap: wrap-reverse;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
