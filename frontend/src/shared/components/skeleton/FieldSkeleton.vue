<script setup lang="ts">
/**
 * The placeholder of one form field: its label above a control of the
 * usual input height, or a taller one for a text area or a rich text editor.
 */
withDefaults(defineProps<{ control?: string; labelWidth?: string }>(), {
  control: '2.75rem',
  labelWidth: '35%',
})
</script>

<template>
  <div class="field-skeleton">
    <Skeleton :width="labelWidth" height="0.875rem" />
    <Skeleton :height="control" />
  </div>
</template>

<style scoped lang="scss">
.field-skeleton {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}
</style>
