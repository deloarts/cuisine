<script setup lang="ts">
/**
 * Shows what importing the picked mail template files would do, one row per
 * file, and uploads the importable ones when the admin confirms, ported from
 * Glados. Each file goes through the backend's import, which reads its
 * `<title>` as the subject and checks that the template renders.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { importMailTemplate, type ContentLocale, type MailTemplateKind } from '@/features/admin-settings/api/mail'
import { isImportable, type MailTemplateImportRow } from '@/features/admin-settings/mailTemplateFile'
import { useAppToast } from '@/core/composables/useAppToast'

const props = defineProps<{ rows: MailTemplateImportRow[] }>()
const visible = defineModel<boolean>('visible', { default: false })
const emit = defineEmits<{ imported: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const importable = computed(() => props.rows.filter(isImportable))
const saving = ref(false)

const SEVERITY: Record<MailTemplateImportRow['status'], 'success' | 'warn' | 'danger' | 'secondary'> = {
  new: 'success',
  replaces: 'warn',
  badName: 'danger',
  unknownKind: 'danger',
  unknownLocale: 'danger',
  noSubject: 'danger',
  duplicate: 'secondary',
}

function kindLabel(kind: string | null): string {
  return kind ? t(`mailSettings.kinds.${kind}.label`) : '–'
}

async function confirmImport() {
  saving.value = true
  let saved = 0
  try {
    for (const row of importable.value) {
      try {
        await importMailTemplate(
          row.kind as MailTemplateKind,
          row.locale as ContentLocale,
          new Blob([row.text], { type: 'text/html' }),
          row.fileName,
        )
        saved += 1
      } catch (err) {
        toast.error(err)
        return
      }
    }
    toast.success(t('mailSettings.import.done', { count: saved }, saved))
    visible.value = false
  } finally {
    saving.value = false
    // Also after a partial import, so the list shows what was saved.
    if (saved) emit('imported')
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('mailSettings.import.title')" class="import-dialog">
    <div class="import-content">
      <p class="hint">{{ t('mailSettings.import.intro') }}</p>
      <ul class="rows">
        <li v-for="row in rows" :key="row.fileName" class="row">
          <span class="row-text">
            <code>{{ row.fileName }}</code>
            <small class="text-muted">{{ kindLabel(row.kind) }}<template v-if="row.locale"> · {{ row.locale }}</template></small>
          </span>
          <Tag :value="t(`mailSettings.import.status.${row.status}`)" :severity="SEVERITY[row.status]" />
        </li>
      </ul>
      <Message v-if="!importable.length" severity="warn" :closable="false">{{ t('mailSettings.import.nothing') }}</Message>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" text :disabled="saving" @click="visible = false" />
      <Button
        :label="t('mailSettings.import.action', { count: importable.length }, importable.length)"
        icon="mdi mdi-file-import-outline"
        :loading="saving"
        :disabled="!importable.length"
        @click="confirmImport"
      />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
.import-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.import-content {
  display: grid;
  gap: var(--space-3);
}

.rows {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.row-text {
  display: grid;
}
</style>
