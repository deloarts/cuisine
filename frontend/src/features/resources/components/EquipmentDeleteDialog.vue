<script setup lang="ts">
/**
 * Deleting or merging a piece of equipment. A seeded item cannot be
 * deleted; one that recipe steps use is blocked (the dialog names the
 * recipes the reader may see) and can be merged into another item, which
 * repoints the steps and kitchens and keeps the merged names as other names
 * of the target. An unused item is deleted after a confirmation.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { EquipmentResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  deleteEquipment,
  equipmentDeletionImpact,
  mergeEquipment,
  type EquipmentDeletionImpact,
} from '@/features/resources/api/resources'
import DialogBodySkeleton from '@/shared/components/skeleton/DialogBodySkeleton.vue'

const visible = defineModel<boolean>('visible', { required: true })
const props = withDefaults(
  defineProps<{ item: EquipmentResponse | null; catalogue: EquipmentResponse[]; mode?: 'delete' | 'merge' }>(),
  { mode: 'delete' },
)
const emit = defineEmits<{ done: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const impact = ref<EquipmentDeletionImpact | null>(null)
const merging = ref(false)
const intoId = ref<string | null>(null)
const busy = ref(false)

const name = computed(() => props.item?.name ?? '')
// Items of the same kind come first, since a merge usually stays within one.
const targets = computed(() => {
  const item = props.item
  if (!item) return []
  return props.catalogue
    .filter((e) => e.id !== item.id)
    .sort((a, b) => Number(b.kind === item.kind) - Number(a.kind === item.kind) || a.name.localeCompare(b.name))
})
const hidden = computed(() => (impact.value ? impact.value.recipe_count - impact.value.recipes.length : 0))

watch(visible, async (open) => {
  if (!open || !props.item) return
  impact.value = null
  intoId.value = null
  merging.value = props.mode === 'merge'
  try {
    impact.value = await equipmentDeletionImpact(props.item.id)
  } catch (err) {
    toast.error(err)
    visible.value = false
  }
})

async function run(action: () => Promise<unknown>) {
  busy.value = true
  try {
    await action()
    toast.success(t('common.done'))
    visible.value = false
    emit('done')
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

function merge() {
  const item = props.item
  const target = intoId.value
  if (item && target) void run(() => mergeEquipment(item.id, target))
}

function remove() {
  const item = props.item
  if (item) void run(() => deleteEquipment(item.id))
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="merging ? t('resources.equipment.mergeTitle') : t('resources.equipment.deleteTitle')"
    class="resource-dialog"
  >
    <DialogBodySkeleton v-if="!impact" :label="t('resources.loading')" />

    <form v-else-if="merging" class="dialog-form" @submit.prevent="merge">
      <p>{{ t('resources.equipment.mergeText', { name }) }}</p>
      <Message v-if="impact.seeded" severity="info" :closable="false">{{ t('resources.equipment.mergeSeeded') }}</Message>
      <div class="field">
        <label id="equipment-merge-label" for="equipment-merge">{{ t('resources.units.mergeInto') }}</label>
        <Select
          id="equipment-merge"
          v-model="intoId"
          :options="targets"
          option-label="name"
          option-value="id"
          aria-labelledby="equipment-merge-label"
          filter
          fluid
        >
          <template #option="{ option }">
            {{ option.name }} <small class="text-muted">{{ t(`equipmentKinds.${option.kind}`) }}</small>
          </template>
        </Select>
      </div>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button
          type="submit"
          :label="t('resources.merge')"
          icon="mdi mdi-call-merge"
          severity="danger"
          :disabled="!intoId || impact.seeded"
          :loading="busy"
        />
      </div>
    </form>

    <div v-else-if="impact.seeded" class="dialog-form">
      <Message severity="info" :closable="false">{{ t('resources.equipment.seeded', { name }) }}</Message>
      <div class="dialog-actions">
        <Button :label="t('common.close')" severity="secondary" @click="visible = false" />
      </div>
    </div>

    <div v-else-if="impact.recipe_count > 0" class="dialog-form">
      <Message severity="warn" :closable="false">
        {{ t('resources.equipment.inUse', { name, count: impact.recipe_count }, impact.recipe_count) }}
      </Message>
      <ul v-if="impact.recipes.length" class="recipe-list">
        <li v-for="recipe in impact.recipes" :key="recipe.id">
          <RouterLink :to="{ name: 'recipe', params: { id: recipe.id } }" @click="visible = false">
            {{ recipe.title }}
          </RouterLink>
        </li>
      </ul>
      <p v-if="hidden > 0" class="hint">{{ t('resources.equipment.hidden', { count: hidden }, hidden) }}</p>
      <div class="dialog-actions">
        <Button :label="t('common.close')" text severity="secondary" @click="visible = false" />
        <Button
          v-if="impact.can_merge"
          :label="t('resources.equipment.mergeOpen')"
          icon="mdi mdi-call-merge"
          @click="merging = true"
        />
      </div>
    </div>

    <div v-else class="dialog-form">
      <p>{{ t('resources.equipment.deleteConfirm', { name }) }}</p>
      <div class="dialog-actions">
        <Button :label="t('common.cancel')" text @click="visible = false" />
        <Button :label="t('common.delete')" icon="mdi mdi-delete-outline" severity="danger" :loading="busy" @click="remove" />
      </div>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
@use './resourceTab';

.recipe-list {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-5);
}
</style>
