<script setup lang="ts">
/**
 * Live readings of the machine and the app, read fresh on every visit and
 * every refresh and never stored: versions, uptime, CPU, memory, disk, and
 * whether the database and Redis answer. Until the first readings arrive the
 * section shows its whole structure with a skeleton in place of each value.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { getHostStatus, type HostStatus } from '@/features/admin-settings/api/system'
import { formatBytes, formatUptime } from '@/features/admin-settings/format'
import { useAppToast } from '@/core/composables/useAppToast'

const { t, locale } = useI18n()
const toast = useAppToast()
const host = ref<HostStatus | null>(null)
const loading = ref(false)
const tag = computed(() => contentLocaleOf(locale.value))

async function load() {
  loading.value = true
  try {
    host.value = await getHostStatus()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function serviceSeverity(status: string): 'success' | 'warn' | 'danger' {
  if (status === 'ok') return 'success'
  return status === 'degraded' ? 'warn' : 'danger'
}

// The readings are live, so they refresh every ten seconds while the tab is open.
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  void load()
  timer = setInterval(() => void load(), 10_000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="settings-tab" :aria-busy="!host">
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.host.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text @click="load" />
      </div>
    </div>
    <dl class="readings">
      <div class="reading">
        <dt>{{ t('adminArea.host.app') }}</dt>
        <dd>
          <template v-if="host">{{ host.app_version }}</template>
          <Skeleton v-else width="5rem" height="1rem" class="reading-skeleton" />
        </dd>
      </div>
      <div class="reading">
        <dt>{{ t('adminArea.host.machine') }}</dt>
        <dd>
          <template v-if="host">{{ host.hostname }} · {{ host.platform }}</template>
          <Skeleton v-else width="12rem" height="1rem" class="reading-skeleton" />
        </dd>
      </div>
      <div class="reading">
        <dt>{{ t('adminArea.host.python') }}</dt>
        <dd>
          <template v-if="host">{{ host.python_version }}</template>
          <Skeleton v-else width="4rem" height="1rem" class="reading-skeleton" />
        </dd>
      </div>
      <div class="reading">
        <dt>{{ t('adminArea.host.uptime') }}</dt>
        <dd>
          <template v-if="host">
            {{ t('adminArea.host.appUptime', { value: formatUptime(host.process_start_time) }) }}
            · {{ t('adminArea.host.machineUptime', { value: formatUptime(host.boot_time) }) }}
          </template>
          <Skeleton v-else width="14rem" height="1rem" class="reading-skeleton" />
        </dd>
      </div>
    </dl>
    <div class="meters">
      <div class="meter">
        <span class="meter-label">
          {{ host ? t('adminArea.host.cpu', { count: host.cpu_count }) : t('adminArea.host.cpuLabel') }}
        </span>
        <ProgressBar v-if="host" :value="Math.round(host.cpu_percent)" :aria-label="t('adminArea.host.cpuLabel')" />
        <Skeleton v-else height="1.25rem" />
        <small class="text-muted">
          <template v-if="host?.load_average">
            {{ t('adminArea.host.load') }} {{ host.load_average.map((l) => l.toFixed(2)).join(' / ') }}
          </template>
          <Skeleton v-else-if="!host" width="9rem" height="0.85rem" class="reading-skeleton" />
        </small>
      </div>
      <div class="meter">
        <span class="meter-label">{{ t('adminArea.host.memory') }}</span>
        <ProgressBar v-if="host" :value="Math.round(host.memory_percent)" :aria-label="t('adminArea.host.memory')" />
        <Skeleton v-else height="1.25rem" />
        <small class="text-muted">
          <template v-if="host">
            {{ formatBytes(host.memory_used_bytes, tag) }} / {{ formatBytes(host.memory_total_bytes, tag) }}
          </template>
          <Skeleton v-else width="9rem" height="0.85rem" class="reading-skeleton" />
        </small>
      </div>
      <div class="meter">
        <span class="meter-label">{{ t('adminArea.host.disk') }} <code v-if="host">{{ host.disk_path }}</code></span>
        <ProgressBar v-if="host" :value="Math.round(host.disk_percent)" :aria-label="t('adminArea.host.disk')" />
        <Skeleton v-else height="1.25rem" />
        <small class="text-muted">
          <template v-if="host">
            {{ formatBytes(host.disk_used_bytes, tag) }} / {{ formatBytes(host.disk_total_bytes, tag) }}
          </template>
          <Skeleton v-else width="9rem" height="0.85rem" class="reading-skeleton" />
        </small>
      </div>
    </div>
    <h3 class="panel-title">{{ t('adminArea.host.services') }}</h3>
    <ul v-if="!host" class="services" aria-hidden="true">
      <li v-for="n in 2" :key="n" class="service">
        <Skeleton width="2.5rem" height="1.5rem" />
        <Skeleton width="8rem" height="1rem" />
      </li>
    </ul>
    <ul v-else class="services">
      <li v-for="service in host.services" :key="service.name" class="service">
        <Tag :value="service.status" :severity="serviceSeverity(service.status)" />
        <strong>{{ service.name }}</strong>
        <small class="text-muted">
          <template v-if="service.version">{{ service.version }}</template>
          <template v-if="service.latency_ms !== null"> · {{ Math.round(service.latency_ms) }} ms</template>
          <template v-if="service.detail"> · {{ service.detail }}</template>
        </small>
      </li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.readings {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.reading {
  display: grid;

  dt {
    font-size: var(--font-size-sm);
    color: var(--p-text-muted-color);
  }

  dd {
    margin: 0;
    font-weight: 700;
  }
}

.meters {
  display: grid;
  gap: var(--space-3);
}

.meter {
  display: grid;
  gap: var(--space-1);
}

.services {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.service {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

@media (min-width: $bp-sm) {
  .readings {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .meters {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

// A placeholder sits on the line its value takes, so nothing moves when the
// readings arrive.
.reading-skeleton {
  display: inline-block;
  vertical-align: middle;
}
</style>
