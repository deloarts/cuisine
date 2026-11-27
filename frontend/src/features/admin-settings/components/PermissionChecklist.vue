<script setup lang="ts">
// The permission checkboxes of the user and group dialogs, grouped by area.
// In the user dialog the permissions a selected group grants are shown
// checked and disabled, since only the group can take them away, and a
// direct grant a group also gives can be dropped from here. A permission
// the editor does not hold is shown but cannot be changed, because nobody
// can grant what they do not hold.
import { useI18n } from 'vue-i18n'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { PERMISSION_GROUPS, permissionLabelKey } from '@/shared/utils/permissionGroups'

const props = withDefaults(
  defineProps<{
    /** Prefixes the checkbox ids, so each dialog keeps its own. */
    idPrefix: string
    /** The id of the caption that names the list. */
    labelledby: string
    /** Every permission the selected groups grant, with the names of the groups granting it. */
    inherited?: Map<string, string[]>
  }>(),
  { inherited: () => new Map<string, string[]>() },
)

/** The direct grants only; the groups add theirs on top. */
const permissions = defineModel<string[]>('permissions', { required: true })

const { t } = useI18n()
const currentUser = useCurrentUserStore()

function inputId(perm: string): string {
  return `${props.idPrefix}-${perm.replace(':', '-')}`
}

function held(perm: string): boolean {
  return currentUser.hasPermission(perm)
}

/** Why a row looks the way it does, or nothing for an ordinary row. */
function note(perm: string): string | null {
  const groups = props.inherited.get(perm)
  if (groups) {
    const names = groups.join(', ')
    return permissions.value.includes(perm)
      ? t('permissionChecklist.alsoDirect', { groups: names })
      : t('permissionChecklist.fromGroups', { groups: names })
  }
  return held(perm) ? null : t('permissionChecklist.notHeld')
}

function dropDirectGrant(perm: string): void {
  permissions.value = permissions.value.filter((p) => p !== perm)
}
</script>

<template>
  <div role="group" :aria-labelledby="labelledby" class="permission-checklist">
    <section v-for="section in PERMISSION_GROUPS" :key="section.titleKey" class="permission-section">
      <h3 class="section-title">
        <span :class="['mdi', section.icon]" aria-hidden="true" />
        {{ t(section.titleKey) }}
      </h3>
      <div
        v-for="perm in section.permissions"
        :key="perm"
        v-tooltip.left="note(perm) ? { value: note(perm), showDelay: 300 } : undefined"
        class="permission-item"
        :data-testid="`permission-row-${perm}`"
      >
        <span v-if="note(perm)" :id="`${inputId(perm)}-note`" class="visually-hidden">{{ note(perm) }}</span>
        <!-- Inherited from a group: shown checked and disabled, since only
             the group can take it away. -->
        <template v-if="inherited.has(perm)">
          <Checkbox
            :input-id="inputId(perm)"
            :model-value="true"
            binary
            disabled
            :pt="{ input: { 'aria-describedby': `${inputId(perm)}-note` } }"
            :data-testid="`inherited-${perm}`"
          />
          <label :for="inputId(perm)" class="muted-label">{{ t(permissionLabelKey(perm)) }}</label>
          <Button
            v-if="permissions.includes(perm) && held(perm)"
            v-tooltip.top="t('permissionChecklist.dropDirect')"
            type="button"
            icon="mdi mdi-close"
            size="small"
            severity="secondary"
            text
            rounded
            class="drop-direct"
            :aria-label="t('permissionChecklist.dropDirect')"
            :data-testid="`drop-direct-${perm}`"
            @click="dropDirectGrant(perm)"
          />
        </template>
        <template v-else>
          <Checkbox
            v-model="permissions"
            :input-id="inputId(perm)"
            :value="perm"
            :disabled="!held(perm)"
            :pt="note(perm) ? { input: { 'aria-describedby': `${inputId(perm)}-note` } } : undefined"
          />
          <label :for="inputId(perm)" :class="{ 'muted-label': !held(perm) }">{{ t(permissionLabelKey(perm)) }}</label>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.permission-checklist {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.permission-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}

.permission-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 1.5rem;

  label {
    font-size: var(--font-size-sm);
    cursor: pointer;
  }
}

.muted-label {
  color: var(--p-text-muted-color);
}

// Keeps the row as tall as the others.
.drop-direct {
  width: 1.5rem;
  height: 1.5rem;
}
</style>
