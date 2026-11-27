<script setup lang="ts">
/**
 * Dialog notices: a message every user sees once in a dialog after signing
 * in and confirms with a click. The overview shows who confirmed and who
 * has not yet.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import RichTextEditor from '@/shared/components/richText/RichTextEditor.vue'
import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'
import type { ContentLocale } from '@/shared/cookbook/types'
import {
  noticesApi,
  type AcknowledgementOverview,
  type AdminNotice,
  type NoticeText,
} from '@/features/admin-settings/api/notifications'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const notices = ref<AdminNotice[]>([])
const loaded = ref(false)
const dialog = ref(false)
const editing = ref<AdminNotice | null>(null)
const texts = ref<Record<ContentLocale, NoticeText>>(emptyTexts())
const active = ref(true)
const saving = ref(false)
const overview = ref<AcknowledgementOverview | null>(null)
const overviewOpen = ref(false)

interface AcknowledgementRow {
  id: string
  name: string
  confirmed: boolean
  at: string | null
}

const ackTable = useResourceTable('acknowledgements', { ackQ: 'string', ackState: 'string' })
const ackRows = computed<AcknowledgementRow[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    ...o.acknowledged.map((a) => ({ id: a.user.id, name: a.user.display_name, confirmed: true, at: a.acknowledged_at })),
    ...o.pending.map((p) => ({ id: p.id, name: p.display_name, confirmed: false, at: null })),
  ].filter(
    (row) =>
      matchesText(ackTable.filters.ackQ, row.name) &&
      (!ackTable.filters.ackState || (ackTable.filters.ackState === 'confirmed') === row.confirmed),
  )
})
const ackColumns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('users.fullName'), filter: true },
  { field: 'confirmed', header: t('users.status'), filter: true },
  { field: 'at', header: t('adminArea.notices.confirmedAt') },
])
const ackStateOptions = computed(() => [
  { value: 'confirmed', label: t('adminArea.notices.stateConfirmed') },
  { value: 'waiting', label: t('adminArea.notices.stateWaiting') },
])

const own = computed(() => contentLocaleOf(locale.value))

function emptyTexts(): Record<ContentLocale, NoticeText> {
  return { 'en-GB': { title: '', body: '' }, 'de-AT': { title: '', body: '' } }
}

function title(notice: AdminNotice): string {
  return notice.texts[own.value]?.title || notice.texts['en-GB']?.title || Object.values(notice.texts)[0]?.title || '–'
}

async function load() {
  try {
    notices.value = await noticesApi.list()
    loaded.value = true
  } catch (err) {
    toast.error(err)
  }
}

function open(notice: AdminNotice | null) {
  editing.value = notice
  const next = emptyTexts()
  for (const l of CONTENT_LOCALES) {
    next[l] = { title: notice?.texts[l]?.title ?? '', body: notice?.texts[l]?.body ?? '' }
  }
  texts.value = next
  active.value = notice?.active ?? true
  dialog.value = true
}

async function submit() {
  saving.value = true
  try {
    const body = { texts: texts.value, active: active.value }
    if (editing.value) await noticesApi.update(editing.value.id, body)
    else await noticesApi.create(body)
    dialog.value = false
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

function remove(notice: AdminNotice) {
  confirm.require({
    message: t('adminArea.notices.deleteConfirm', { title: title(notice) }),
    header: t('common.confirm'),
    acceptProps: { label: t('common.delete'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void noticesApi
        .remove(notice.id)
        .then(load)
        .catch((err: unknown) => toast.error(err))
    },
  })
}

async function showOverview(notice: AdminNotice) {
  try {
    overview.value = await noticesApi.acknowledgements(notice.id)
    overviewOpen.value = true
  } catch (err) {
    toast.error(err)
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.notices.title') }}</h2>
      <div v-if="canWrite" class="section-actions">
        <Button :label="t('adminArea.notices.create')" icon="mdi mdi-plus" @click="open(null)" />
      </div>
    </div>
    <p class="hint">{{ t('adminArea.notices.hint') }}</p>
    <ul v-if="notices.length" class="notice-list">
      <li v-for="notice in notices" :key="notice.id" class="notice-row">
        <span class="notice-text">
          <strong>{{ title(notice) }}</strong>
          <small class="text-muted">
            {{ t('adminArea.notices.progress', { done: notice.acknowledged, total: notice.audience }) }}
          </small>
        </span>
        <Tag
          :value="notice.active ? t('adminArea.notices.active') : t('adminArea.notices.inactive')"
          :severity="notice.active ? 'success' : 'secondary'"
        />
        <Button icon="mdi mdi-account-check-outline" text rounded :aria-label="t('adminArea.notices.overview')" @click="showOverview(notice)" />
        <template v-if="canWrite">
          <Button icon="mdi mdi-pencil" text rounded :aria-label="t('common.edit')" @click="open(notice)" />
          <Button icon="mdi mdi-delete-outline" text rounded severity="danger" :aria-label="t('common.delete')" @click="remove(notice)" />
        </template>
      </li>
    </ul>
    <p v-else-if="loaded" class="empty-note">{{ t('adminArea.notices.none') }}</p>

    <Dialog v-model:visible="dialog" modal :header="t('adminArea.notices.edit')" class="notice-dialog">
      <form class="notice-form" @submit.prevent="submit">
        <fieldset v-for="l in CONTENT_LOCALES" :key="l" class="notice-locale">
          <legend>{{ t(`contentLocales.${l.replace('-', '')}`) }}</legend>
          <div class="field">
            <label :for="`notice-title-${l}`">{{ t('adminArea.notices.noticeTitle') }}</label>
            <InputText :id="`notice-title-${l}`" v-model="texts[l].title" fluid />
          </div>
          <div class="field">
            <span :id="`notice-body-${l}`" class="field-label">{{ t('adminArea.notices.body') }}</span>
            <RichTextEditor v-model="texts[l].body" :labelledby="`notice-body-${l}`" :rows="5" />
          </div>
        </fieldset>
        <div class="field toggle-field">
          <ToggleSwitch v-model="active" input-id="notice-active" />
          <label for="notice-active">{{ t('adminArea.notices.activeLabel') }}</label>
        </div>
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="dialog = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="overviewOpen" modal :header="t('adminArea.notices.overview')" class="notice-dialog">
      <template v-if="overview">
        <p class="hint">
          {{ t('adminArea.notices.confirmed', { count: overview.acknowledged.length }) }} ·
          {{ t('adminArea.notices.waiting', { count: overview.pending.length }) }}
        </p>
        <ResourceTable
          :state="ackTable"
          :value="ackRows"
          :columns="ackColumns"
          :fill="false"
          empty-icon="mdi mdi-account-check-outline"
        >
          <template #filter-name>
            <InputText
              v-model="ackTable.filters.ackQ"
              :placeholder="t('tableFilters.search')"
              :aria-label="t('tableFilters.filterBy', { column: t('users.fullName') })"
              size="small"
              fluid
            />
          </template>
          <template #filter-confirmed>
            <Select
              v-model="ackTable.filters.ackState"
              :options="ackStateOptions"
              option-label="label"
              option-value="value"
              :placeholder="t('tableFilters.all')"
              :aria-label="t('tableFilters.filterBy', { column: t('users.status') })"
              show-clear
              size="small"
              fluid
            />
          </template>
          <template #body-confirmed="{ data }">
            <Tag
              :value="data.confirmed ? t('adminArea.notices.stateConfirmed') : t('adminArea.notices.stateWaiting')"
              :severity="data.confirmed ? 'success' : 'secondary'"
            />
          </template>
          <template #body-at="{ data }">{{ data.at ? formatDateTime(data.at, locale as AppLocale) : '' }}</template>
          <template #phone="{ data }">
            {{ data.confirmed ? t('adminArea.notices.stateConfirmed') : t('adminArea.notices.stateWaiting') }}
            <template v-if="data.at"> · {{ formatDateTime(data.at, locale as AppLocale) }}</template>
          </template>
        </ResourceTable>
      </template>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
.notice-list {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.notice-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto auto;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.notice-text {
  display: grid;
}

.notice-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.notice-form {
  display: grid;
  gap: var(--space-3);
}

.notice-locale {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  margin: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
}

.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
