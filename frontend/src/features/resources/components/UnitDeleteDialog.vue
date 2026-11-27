<script setup lang="ts">
/**
 * Deleting a unit. The dialog first asks what the deletion would touch: a
 * seeded unit cannot go at all, a custom unit that recipes, conversions or
 * shopping items still use can only be merged into another unit (which
 * repoints all of them), and an unused one is deleted after a confirmation.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { UnitResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  deleteUnit,
  mergeUnit,
  unitDeletionImpact,
  type UnitDeletionImpact,
} from '@/features/resources/api/resources'
import DialogBodySkeleton from '@/shared/components/skeleton/DialogBodySkeleton.vue'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ unit: UnitResponse | null; units: UnitResponse[] }>()
const emit = defineEmits<{ done: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const impact = ref<UnitDeletionImpact | null>(null)
const intoId = ref<string | null>(null)
const busy = ref(false)

// A unit merges best into one of its own kind, so those come first.
const targets = computed(() => {
  const unit = props.unit
  if (!unit) return []
  return props.units
    .filter((u) => u.id !== unit.id)
    .sort((a, b) => Number(b.kind === unit.kind) - Number(a.kind === unit.kind) || a.name.localeCompare(b.name))
})

watch(visible, async (open) => {
  if (!open || !props.unit) return
  impact.value = null
  intoId.value = null
  try {
    impact.value = await unitDeletionImpact(props.unit.id)
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
  const unit = props.unit
  const target = intoId.value
  if (unit && target) void run(() => mergeUnit(unit.id, target))
}

function remove() {
  const unit = props.unit
  if (unit) void run(() => deleteUnit(unit.id))
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('resources.units.deleteTitle')" class="resource-dialog">
    <DialogBodySkeleton v-if="!impact" :label="t('resources.loading')" :actions="1" />
    <div v-else-if="impact.seeded" class="dialog-form">
      <Message severity="info" :closable="false">{{ t('resources.units.seeded', { name: unit?.name }) }}</Message>
      <div class="dialog-actions">
        <Button :label="t('common.close')" severity="secondary" @click="visible = false" />
      </div>
    </div>
    <form v-else-if="impact.in_use" class="dialog-form" @submit.prevent="merge">
      <Message severity="warn" :closable="false">{{ t('resources.units.inUse', { name: unit?.name }) }}</Message>
      <div class="field">
        <label id="unit-merge-label" for="unit-merge">{{ t('resources.units.mergeInto') }}</label>
        <Select
          id="unit-merge"
          v-model="intoId"
          :options="targets"
          option-label="name"
          option-value="id"
          aria-labelledby="unit-merge-label"
          filter
          fluid
        >
          <template #option="{ option }">
            {{ option.name }} <small class="text-muted">{{ t(`resources.unitKinds.${option.kind}`) }}</small>
          </template>
        </Select>
        <small class="field-hint">{{ t('resources.units.mergeHint') }}</small>
      </div>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('resources.merge')" severity="danger" :disabled="!intoId" :loading="busy" />
      </div>
    </form>
    <div v-else class="dialog-form">
      <p>{{ t('resources.units.deleteConfirm', { name: unit?.name }) }}</p>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button :label="t('common.delete')" severity="danger" :loading="busy" @click="remove" />
      </div>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
@use './resourceTab';
</style>
