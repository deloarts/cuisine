<script setup lang="ts">
/**
 * Where the data lives and how big it is: the database and its largest
 * tables, the stored files by kind, and the nightly backups the backup
 * sidecar writes, as far as the backend can see them, with the steps to
 * restore one.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import {
  getRestoreGuidance,
  getStorageStatus,
  requestBackup,
  type RestoreStep,
  type StorageStatus,
} from '@/features/admin-settings/api/system'
import { formatBytes } from '@/features/admin-settings/format'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'

const { t, te, locale } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const storage = ref<StorageStatus | null>(null)
const guidance = ref<RestoreStep[]>([])
const loading = ref(false)
const requesting = ref(false)
const tag = computed(() => contentLocaleOf(locale.value))
// Holds a line until the first readings arrive.
const BLANK = '\u00a0'

async function load() {
  loading.value = true
  try {
    storage.value = await getStorageStatus()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function loadGuidance() {
  try {
    guidance.value = await getRestoreGuidance(tag.value)
  } catch {
    // The built-in steps below stay in place.
    guidance.value = []
  }
}

// The backup sidecar picks the request up within a minute or so; the status
// shows it as requested until the run is done.
async function backUpNow() {
  requesting.value = true
  try {
    await requestBackup()
    toast.success(t('adminArea.storage.backupRequested'))
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    requesting.value = false
  }
}

onMounted(() => {
  void load()
  void loadGuidance()
})
</script>

<template>
  <div class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.storage.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <template v-if="storage">
      <Message v-for="warning in storage.warnings" :key="warning" severity="warn" :closable="false">
        {{ te(`adminArea.storage.warnings.${warning}`) ? t(`adminArea.storage.warnings.${warning}`) : warning }}
      </Message>
    </template>
    <section class="block">
      <h3 class="panel-title">{{ t('adminArea.storage.database') }}</h3>
      <p>
        {{ storage ? `${storage.database.dialect} · ${formatBytes(storage.database.size_bytes, tag)}` : BLANK }}
      </p>
      <ul class="rows">
        <li v-for="table in storage?.database.largest_tables ?? []" :key="table.name" class="row">
          <code>{{ table.name }}</code>
          <span>{{ formatBytes(table.bytes, tag) }}</span>
        </li>
      </ul>
    </section>
    <section class="block">
      <h3 class="panel-title">{{ t('adminArea.storage.files') }}</h3>
      <p>
        <template v-if="storage">
          {{ t('adminArea.storage.fileSummary', { count: storage.files.count }) }} ·
          {{ formatBytes(storage.files.original_bytes, tag) }}
          <small class="text-muted">
            ({{ t('adminArea.storage.thumbnails', { size: formatBytes(storage.files.thumbnail_bytes, tag) }) }})
          </small>
        </template>
        <template v-else>{{ BLANK }}</template>
      </p>
      <p class="text-muted">
        <template v-if="storage">
          {{ t('adminArea.storage.provider', { name: storage.provider }) }}
          <Tag
            :value="storage.provider_reachable ? t('adminArea.storage.reachable') : t('adminArea.storage.unreachable')"
            :severity="storage.provider_reachable ? 'success' : 'danger'"
          />
        </template>
        <template v-else>{{ BLANK }}</template>
      </p>
      <ul class="rows">
        <li v-for="kind in storage?.files.by_kind ?? []" :key="kind.kind" class="row">
          <span>{{ kind.kind }}</span>
          <span>{{ kind.count }} · {{ formatBytes(kind.bytes, tag) }}</span>
        </li>
      </ul>
    </section>
    <section class="block">
      <div class="section-head">
        <h3 class="panel-title">{{ t('adminArea.storage.backups') }}</h3>
        <div v-if="canWrite && storage?.backup_now_available !== false" class="section-actions">
          <Button
            :label="storage?.backup_requested ? t('adminArea.storage.backupPending') : t('adminArea.storage.backupNow')"
            icon="mdi mdi-database-arrow-down-outline"
            outlined
            :disabled="!storage || storage.backup_requested"
            :loading="requesting"
            @click="backUpNow"
          />
        </div>
      </div>
      <template v-if="storage">
        <p v-if="!storage.backup_now_available" class="field-hint">{{ t('adminArea.storage.backupNowUnavailable') }}</p>
        <p v-if="storage.last_run">
          {{
            t(storage.last_run.trigger === 'manual' ? 'adminArea.storage.lastRunManual' : 'adminArea.storage.lastRunScheduled', {
              date: formatDateTime(storage.last_run.started, locale as AppLocale),
            })
          }}
          <Tag
            v-if="storage.last_run.finished"
            :value="storage.last_run.ok ? t('adminArea.storage.runOk') : t('adminArea.storage.runFailed')"
            :severity="storage.last_run.ok ? 'success' : 'danger'"
          />
          <Tag v-else :value="t('adminArea.storage.runRunning')" severity="info" />
        </p>
        <template v-if="storage.backups.visible">
          <p>
            {{ t('adminArea.storage.schedule', { hour: storage.backups.hour_utc, days: storage.backups.keep_days }) }}
          </p>
          <p>
            {{ t('adminArea.storage.newest') }}
            <strong>{{ formatDateTime(storage.backups.newest, locale as AppLocale) }}</strong>
          </p>
          <ul class="rows">
            <li v-for="file in storage.backups.files" :key="file.name" class="row">
              <code>{{ file.name }}</code>
              <span>{{ formatBytes(file.size_bytes, tag) }} · {{ formatDateTime(file.created, locale as AppLocale) }}</span>
            </li>
          </ul>
        </template>
        <p v-else class="hint">{{ t('adminArea.storage.backupsHidden') }}</p>
      </template>
      <p v-else>{{ BLANK }}</p>
      <h4>{{ t('adminArea.storage.restoreTitle') }}</h4>
      <ol v-if="guidance.length" class="restore">
        <li v-for="(step, index) in guidance" :key="index">
          {{ step.text }}
          <pre v-if="step.command" class="command"><code>{{ step.command }}</code></pre>
        </li>
      </ol>
      <ol v-else class="restore">
        <li>{{ t('adminArea.storage.restore1') }}</li>
        <li>{{ t('adminArea.storage.restore2') }}</li>
        <li>{{ t('adminArea.storage.restore3') }}</li>
      </ol>
      <p class="field-hint">{{ t('adminArea.storage.moveHint') }}</p>
      <p class="field-hint">{{ t('adminArea.storage.restoreDocs') }}</p>
    </section>
  </div>
</template>

<style scoped lang="scss">
.block {
  display: grid;
  gap: var(--space-2);

  p {
    margin: 0;
  }
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
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.restore {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding-left: var(--space-5);
}

.command {
  margin: var(--space-1) 0 0;
  padding: var(--space-2);
  overflow-x: auto;
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-hover-background);
  font-size: var(--font-size-sm);
}
</style>
