<script setup lang="ts">
// The permissions column beside the fields of the user and group dialogs:
// a caption, an optional note, and the checklist in a bordered box that
// scrolls when it is taller than the fields next to it.
import { useId } from 'vue'

import PermissionChecklist from '@/features/admin-settings/components/PermissionChecklist.vue'

defineProps<{
  caption: string
  idPrefix: string
  /** Every permission the selected groups grant, with the names of the groups granting it. */
  inherited?: Map<string, string[]>
  /** Shown instead of the checklist, such as for the system user. */
  replacement?: string | null
}>()

const permissions = defineModel<string[]>('permissions', { required: true })

// Ties the caption to the checklist it names.
const uid = useId()
</script>

<template>
  <aside class="permissions-panel">
    <span :id="`${uid}-caption`" class="panel-caption">{{ caption }}</span>
    <p v-if="replacement" class="field-hint">{{ replacement }}</p>
    <div v-else class="permissions-list">
      <PermissionChecklist
        v-model:permissions="permissions"
        :id-prefix="idPrefix"
        :labelledby="`${uid}-caption`"
        :inherited="inherited"
      />
    </div>
  </aside>
</template>

<style scoped lang="scss">
// Size containment keeps the list from growing the row, so the panel is
// exactly as tall as the fields beside it and the list scrolls inside.
.permissions-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  min-height: 0;
  contain: size;
}

.panel-caption {
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.permissions-list {
  flex: 1;
  min-height: 0;
  padding: var(--space-3);
  overflow-y: auto;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
}

// Below the dialog's two-column width the panel drops below the fields,
// with a height cap of its own.
@media (max-width: $bp-lg) {
  .permissions-panel {
    contain: none;
  }

  .permissions-list {
    flex: none;
    max-height: 20rem;
  }
}
</style>
