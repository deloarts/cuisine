<script setup lang="ts">
/**
 * The frame of a loading placeholder. It announces the wait once to
 * assistive technology while the skeleton shapes inside stay hidden from it,
 * and takes the class of the content it stands in for, so a grid or a list
 * keeps its layout while the data is on its way. A page that shows several
 * placeholders at once marks all but one `silent`, so the wait is announced
 * only once.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{ label?: string; testid?: string; silent?: boolean }>(), {
  label: undefined,
  testid: 'skeleton',
  silent: false,
})

const { t } = useI18n()
const text = computed(() => props.label ?? t('common.loading'))
</script>

<template>
  <div v-if="props.silent" aria-hidden="true" :data-testid="props.testid">
    <slot />
  </div>
  <div v-else role="status" :data-testid="props.testid">
    <span class="visually-hidden">{{ text }}</span>
    <slot />
  </div>
</template>
