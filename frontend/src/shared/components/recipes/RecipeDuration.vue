<script setup lang="ts">
/** A duration in minutes as it reads on a recipe: "45 min", "1 h 15 min". */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{ minutes: number; icon?: boolean }>(), { icon: true })
const { t } = useI18n()

const label = computed(() => {
  const hours = Math.floor(props.minutes / 60)
  const minutes = props.minutes % 60
  if (hours === 0) return t('recipes.duration.minutes', { m: minutes })
  if (minutes === 0) return t('recipes.duration.hours', { h: hours })
  return t('recipes.duration.hoursMinutes', { h: hours, m: minutes })
})
</script>

<template>
  <span class="recipe-duration">
    <span v-if="icon" class="mdi mdi-clock-outline" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<style scoped lang="scss">
.recipe-duration {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  white-space: nowrap;
}
</style>
