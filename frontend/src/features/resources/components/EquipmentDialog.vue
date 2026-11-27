<script setup lang="ts">
/**
 * Creates or edits one piece of kitchen equipment: its kind, names and
 * other names per language, an icon, and whether it counts as basic (pre-
 * ticked when someone sets up their kitchen). While creating, the name is
 * checked for items that probably mean the same thing ("Did you mean
 * Schneebesen?").
 */
import { computed, ref, toRaw, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { watchDebounced } from '@vueuse/core'

import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { EQUIPMENT_KINDS } from '@/shared/cookbook/equipment'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import type { EquipmentKind, EquipmentResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  createEquipment,
  equipmentDuplicates,
  updateEquipment,
  type DuplicateCandidate,
} from '@/features/resources/api/resources'

import IconPicker from './IconPicker.vue'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ item: EquipmentResponse | null }>()
const emit = defineEmits<{ saved: [item: EquipmentResponse] }>()

const { t, locale } = useI18n()
const toast = useAppToast()

const kind = ref<EquipmentKind>('utensil')
const icon = ref<string | null>(null)
const basic = ref(false)
const texts = ref<Record<string, Record<string, string>>>({})
const aliases = ref<Record<string, string[]>>({})
const duplicates = ref<DuplicateCandidate[]>([])
const saving = ref(false)

const ownLocale = computed(() => contentLocaleOf(locale.value))
const ownName = computed(() => texts.value[ownLocale.value]?.name?.trim() ?? '')
const kindOptions = computed(() => EQUIPMENT_KINDS.map((k) => ({ value: k, label: t(`equipmentKinds.${k}`) })))
const exact = computed(() => duplicates.value.find((d) => d.exact) ?? null)
const near = computed(() => duplicates.value.filter((d) => !d.exact))

watch(visible, (open) => {
  if (!open) return
  const item = props.item
  kind.value = (item?.kind as EquipmentKind | undefined) ?? 'utensil'
  icon.value = item?.icon ?? null
  basic.value = item?.basic ?? false
  // The rows are reactive proxies, which structuredClone refuses to copy.
  texts.value = structuredClone(toRaw(item?.translations ?? {}))
  aliases.value = Object.fromEntries(CONTENT_LOCALES.map((l) => [l, [...(item?.aliases[l] ?? [])]]))
  duplicates.value = []
})

watchDebounced(
  ownName,
  async (name) => {
    if (!visible.value || props.item || name.length < 2) {
      duplicates.value = []
      return
    }
    try {
      const found = await equipmentDuplicates(name, ownLocale.value)
      if (ownName.value === name) duplicates.value = found
    } catch {
      duplicates.value = []
    }
  },
  { debounce: 400 },
)

async function submit() {
  const body = {
    kind: kind.value,
    icon: icon.value,
    basic: basic.value,
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => v.name?.trim())
        .map(([l, v]) => [l, { name: (v.name ?? '').trim() }]),
    ),
    aliases: Object.fromEntries(
      Object.entries(aliases.value).map(([l, names]) => [l, [...new Set(names.map((n) => n.trim()).filter(Boolean))]]),
    ),
  }
  saving.value = true
  try {
    const item = props.item
    const saved = item ? await updateEquipment(item.id, body) : await createEquipment(body)
    toast.success(t('common.saved'))
    visible.value = false
    emit('saved', saved)
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="item ? t('resources.equipment.edit') : t('resources.equipment.create')"
    class="resource-dialog"
  >
    <form class="dialog-form" @submit.prevent="submit">
      <div class="form-grid">
        <div class="field">
          <label id="equipment-kind-label" for="equipment-kind">{{ t('resources.equipment.kind') }}</label>
          <Select
            id="equipment-kind"
            v-model="kind"
            :options="kindOptions"
            option-label="label"
            option-value="value"
            aria-labelledby="equipment-kind-label"
            fluid
          />
        </div>
        <div class="field basic-field">
          <ToggleSwitch v-model="basic" input-id="equipment-basic" />
          <label for="equipment-basic">{{ t('resources.equipment.basic') }}</label>
        </div>
      </div>
      <small class="field-hint">{{ t('resources.equipment.basicHint') }}</small>
      <TranslationFields
        v-model="texts"
        id-prefix="equipment"
        :original-locale="ownLocale"
        :fields="[{ key: 'name', label: t('common.name') }]"
      >
        <template #locale="{ locale: l }">
          <div class="field">
            <label :for="`equipment-alias-${l}`">{{ t('resources.equipment.otherNames') }}</label>
            <AutoComplete v-model="aliases[l]" :input-id="`equipment-alias-${l}`" multiple :typeahead="false" fluid />
          </div>
        </template>
      </TranslationFields>
      <Message v-if="exact" severity="error" :closable="false">
        {{ t('resources.equipment.exists', { name: exact.name }) }}
      </Message>
      <Message v-else-if="near.length" severity="warn" :closable="false">
        {{ t('resources.equipment.didYouMean', { names: near.map((d) => d.name).join(', ') }) }}
      </Message>
      <div class="field">
        <label for="equipment-icon">{{ t('resources.equipment.icon') }}</label>
        <IconPicker v-model="icon" input-id="equipment-icon" />
      </div>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
@use './resourceTab';

.basic-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  align-self: end;
}
</style>
