<script setup lang="ts">
/**
 * Deletes another user's account for good. The dialog reads what the
 * deletion touches for this user, asks who takes over their recipes and
 * ingredients (or nobody, and then what happens to the recipes), says how
 * long the backups still hold the data, and deletes only after the admin
 * typed the e-mail address.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  canDelete,
  defaultForm,
  deletionQuery,
  keepAllowed,
  lockedRecipes,
  needsOwnerChoice,
  needsVisibilityChoice,
  normaliseForm,
  recipeTotal,
  type DeletionForm,
  type DeletionImpact,
  type OwnerlessVisibility,
} from '@/features/admin-settings/deletionRules'
import { usersApi } from '@/features/admin-settings/api/users'
import { useAppToast } from '@/core/composables/useAppToast'
import type { UserResponse } from '@/core/types/user'
import { formatDate } from '@/core/utils/dates'

const props = defineProps<{ user: UserResponse | null; users: UserResponse[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ deleted: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const impact = ref<DeletionImpact | null>(null)
const form = ref<DeletionForm>(defaultForm())
const typed = ref('')
const loading = ref(false)
const deleting = ref(false)

const owners = computed(() =>
  props.users
    .filter((u) => u.is_active && u.id !== props.user?.id)
    .sort((a, b) => a.full_name.localeCompare(b.full_name)),
)
const visibilityOptions: OwnerlessVisibility[] = ['keep', 'instance', 'delete']
const ready = computed(() =>
  impact.value && props.user ? canDelete(form.value, impact.value, typed.value, props.user.email) : false,
)

/** A date-only string as a local date, so no time zone moves it a day. */
function localDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1)
}

watch(visible, async (open) => {
  if (!open || !props.user) return
  impact.value = null
  form.value = defaultForm()
  typed.value = ''
  loading.value = true
  try {
    impact.value = await usersApi.deletionImpact(props.user.id)
  } catch (err) {
    toast.error(err)
    visible.value = false
  } finally {
    loading.value = false
  }
})

watch(
  () => form.value.visibility,
  () => {
    if (impact.value) form.value = normaliseForm(form.value, impact.value)
  },
)

async function remove() {
  const user = props.user
  const query = impact.value ? deletionQuery(form.value, impact.value) : null
  if (!user || !query || !ready.value) return
  deleting.value = true
  try {
    await usersApi.remove(user.id, query)
    toast.success(t('userDeletion.deleted', { name: user.full_name }))
    visible.value = false
    emit('deleted')
  } catch (err) {
    toast.error(err)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('userDeletion.title', { name: user?.full_name ?? '' })"
    class="deletion-dialog"
  >
    <div v-if="loading" class="hint">{{ t('userDeletion.loading') }}</div>
    <form v-else-if="impact && user" class="deletion" @submit.prevent="remove">
      <section class="block">
        <h3 class="block-title">{{ t('userDeletion.removedTitle') }}</h3>
        <p>{{ t('userDeletion.removed') }}</p>
        <ul class="facts">
          <li v-if="impact.drafts">{{ t('userDeletion.drafts', { count: impact.drafts }, impact.drafts) }}</li>
          <li v-if="impact.in_household">{{ t('userDeletion.household') }}</li>
          <li v-if="impact.lists_handed_over">
            {{ t('userDeletion.listsHandedOver', { count: impact.lists_handed_over }, impact.lists_handed_over) }}
          </li>
          <li v-if="impact.lists_deleted">
            {{ t('userDeletion.listsDeleted', { count: impact.lists_deleted }, impact.lists_deleted) }}
          </li>
          <li>{{ t('userDeletion.securityEvent') }}</li>
        </ul>
      </section>

      <section v-if="needsOwnerChoice(impact)" class="block">
        <h3 class="block-title">{{ t('userDeletion.handoverTitle') }}</h3>
        <p>
          {{
            t('userDeletion.owned', {
              recipes: t('userDeletion.recipeCount', { count: recipeTotal(impact) }, recipeTotal(impact)),
              ingredients: t('userDeletion.ingredientCount', { count: impact.ingredients }, impact.ingredients),
            })
          }}
        </p>
        <div class="choice">
          <RadioButton v-model="form.owner" input-id="deletion-transfer" value="transfer" />
          <label for="deletion-transfer">{{ t('userDeletion.transfer') }}</label>
        </div>
        <div v-if="form.owner === 'transfer'" class="field nested">
          <label id="deletion-owner-label" for="deletion-owner">{{ t('userDeletion.newOwner') }}</label>
          <Select
            id="deletion-owner"
            v-model="form.newOwnerId"
            :options="owners"
            option-label="full_name"
            option-value="id"
            aria-labelledby="deletion-owner-label"
            filter
            fluid
          />
        </div>
        <div class="choice">
          <RadioButton v-model="form.owner" input-id="deletion-nobody" value="nobody" />
          <label for="deletion-nobody">{{ t('userDeletion.nobody') }}</label>
        </div>
        <p v-if="form.owner === 'nobody'" class="hint nested">{{ t('userDeletion.nobodyHint') }}</p>

        <fieldset v-if="needsVisibilityChoice(form, impact)" class="nested visibility">
          <legend class="field-label">{{ t('userDeletion.visibilityTitle') }}</legend>
          <div v-for="option in visibilityOptions" :key="option" class="choice">
            <RadioButton
              v-model="form.visibility"
              :input-id="`deletion-visibility-${option}`"
              :value="option"
              :disabled="option === 'keep' && !keepAllowed(impact)"
            />
            <label :for="`deletion-visibility-${option}`">{{ t(`userDeletion.visibility.${option}`) }}</label>
          </div>
          <Message v-if="!keepAllowed(impact)" severity="info" size="small">
            {{ t('userDeletion.keepLocked', { count: lockedRecipes(impact) }, lockedRecipes(impact)) }}
          </Message>
        </fieldset>
      </section>

      <Message severity="warn">
        {{
          t('userDeletion.backups', {
            days: impact.backup_keep_days,
            date: formatDate(localDate(impact.backups_clear_by)),
          })
        }}
      </Message>

      <div class="field">
        <label for="deletion-confirm">{{ t('userDeletion.typeEmail', { email: user.email }) }}</label>
        <InputText id="deletion-confirm" v-model="typed" autocomplete="off" spellcheck="false" fluid />
      </div>

      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button
          type="submit"
          :label="t('userDeletion.delete')"
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
  gap: var(--space-2);

  p {
    margin: 0;
  }
}

.block-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.facts {
  display: grid;
  gap: var(--space-1);
  padding-left: var(--space-4);
  margin: 0;
}

.choice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.nested {
  margin-left: var(--space-5);
}

.visibility {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  border: 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
