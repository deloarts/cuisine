<script setup lang="ts">
/**
 * Picks an @mdi/font icon for a piece of equipment: a grid of kitchen icons
 * to tap, and a field for any other icon name with a live preview. The value
 * is the icon name without the `mdi-` prefix, or null for none.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const KITCHEN_ICONS = [
  'pot',
  'pot-steam',
  'pot-mix',
  'pan',
  'kettle',
  'bowl',
  'bowl-mix',
  'bowl-outline',
  'knife',
  'silverware-fork-knife',
  'silverware-spoon',
  'scissors-cutting',
  'scale',
  'thermometer',
  'timer-outline',
  'cup-water',
  'blender',
  'microwave',
  'toaster',
  'stove',
  'toaster-oven',
  'fridge-outline',
  'grill',
  'fan',
  'cake',
  'cake-variant',
  'cupcake',
  'cookie',
  'baguette',
  'pizza',
  'pasta',
  'mortar-pestle',
  'filter',
  'cheese',
  'spray',
  'coffee-maker',
]

const props = withDefaults(defineProps<{ inputId: string; disabled?: boolean }>(), { disabled: false })
const icon = defineModel<string | null>({ required: true })

const { t } = useI18n()

const typed = computed({
  get: () => icon.value ?? '',
  set: (value: string) => {
    const name = value.trim().replace(/^mdi[- ]/, '')
    icon.value = name || null
  },
})
</script>

<template>
  <div class="icon-picker">
    <div class="icon-grid" role="group" :aria-label="t('resources.equipment.iconChoices')">
      <button
        v-for="name in KITCHEN_ICONS"
        :key="name"
        type="button"
        class="icon-choice"
        :class="{ 'icon-choice-on': icon === name }"
        :aria-pressed="icon === name"
        :aria-label="name"
        :title="name"
        :disabled="props.disabled"
        @click="icon = icon === name ? null : name"
      >
        <i :class="`mdi mdi-${name}`" aria-hidden="true" />
      </button>
    </div>
    <div class="icon-typed">
      <i :class="`mdi mdi-${icon || 'help-circle-outline'}`" class="icon-preview" aria-hidden="true" />
      <InputText
        :id="inputId"
        v-model="typed"
        :placeholder="t('resources.equipment.iconPlaceholder')"
        :disabled="props.disabled"
        fluid
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.icon-picker {
  display: grid;
  gap: var(--space-2);
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(2.75rem, 1fr));
  gap: var(--space-1);
}

.icon-choice {
  display: grid;
  place-items: center;
  min-height: 2.75rem;
  font-size: var(--font-size-xl);
  color: var(--p-text-color);
  cursor: pointer;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
}

.icon-choice-on {
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.icon-typed {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.icon-preview {
  font-size: var(--font-size-2xl);
}
</style>
