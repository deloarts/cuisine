<script setup lang="ts">
/**
 * Agent access over MCP: the switch, the per-token rate limits and the
 * longest a token carrying `use:mcp` may live, then whether hosted AI clients
 * (ChatGPT, claude.ai) may connect through OAuth and which hosts they may
 * redirect to. Below it, for whoever reads the security log, every agent
 * call on the instance.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AgentCallTable from '@/shared/components/AgentCallTable.vue'
import { getAgentSettings, saveAgentSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const canRead = currentUser.hasPermission(Permission.READ_SETTINGS)
const canWrite = currentUser.hasPermission(Permission.WRITE_SETTINGS)
const canReadLog = currentUser.hasPermission(Permission.READ_SECURITY_LOG)

const { form, loaded, adopt, value } = useSettingsForm<Schemas['AgentSettingsSchema']>(
  {
    enabled: false,
    calls_per_minute: null,
    drafts_per_hour: null,
    token_max_lifetime_days: null,
    oauth_enabled: false,
    oauth_redirect_hosts: [],
  },
  () => getAgentSettings(),
  canRead,
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)

// The allowlist is edited as one host per line; the backend trims, lowers
// and deduplicates the entries and refuses anything that is not a host name.
const hostsText = ref('')
watch(
  () => form.value.oauth_redirect_hosts,
  (hosts) => {
    hostsText.value = (hosts ?? []).join('\n')
  },
  { immediate: true },
)

function hostLines(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    const body = { ...value(), oauth_redirect_hosts: hostLines(hostsText.value) }
    adopt(await saveAgentSettings(body))
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="settings-tab">
    <form v-if="canRead" class="agents-form" @submit.prevent="save">
      <h2 class="panel-title">{{ t('agentSettings.title') }}</h2>
      <p class="hint">{{ t('agentSettings.hint') }}</p>
      <div class="settings-fields">
        <div class="field toggle-field">
          <ToggleSwitch v-model="form.enabled" input-id="agents-enabled" :disabled="!editable" />
          <label for="agents-enabled">{{ t('agentSettings.enabled') }}</label>
        </div>
        <div class="field">
          <label for="agents-cpm">{{ t('agentSettings.callsPerMinute') }}</label>
          <InputNumber v-model="form.calls_per_minute" input-id="agents-cpm" :min="1" :disabled="!editable" />
        </div>
        <div class="field">
          <label for="agents-dph">{{ t('agentSettings.draftsPerHour') }}</label>
          <InputNumber v-model="form.drafts_per_hour" input-id="agents-dph" :min="1" :disabled="!editable" />
        </div>
        <div class="field">
          <label for="agents-days">{{ t('agentSettings.tokenDays') }}</label>
          <InputNumber v-model="form.token_max_lifetime_days" input-id="agents-days" :min="1" :disabled="!editable" />
        </div>
      </div>
      <h3 class="section-title">{{ t('agentSettings.oauthTitle') }}</h3>
      <p class="hint">{{ t('agentSettings.oauthHint') }}</p>
      <div class="settings-fields">
        <div class="field toggle-field">
          <ToggleSwitch
            v-model="form.oauth_enabled"
            input-id="agents-oauth"
            :disabled="!editable || !form.enabled"
          />
          <label for="agents-oauth">{{ t('agentSettings.oauthEnabled') }}</label>
        </div>
        <div class="field">
          <label for="agents-hosts">{{ t('agentSettings.redirectHosts') }}</label>
          <Textarea
            id="agents-hosts"
            v-model="hostsText"
            rows="3"
            auto-resize
            :placeholder="'chatgpt.com\nclaude.ai'"
            :disabled="!editable || !form.oauth_enabled"
            aria-describedby="agents-hosts-hint"
          />
          <small id="agents-hosts-hint" class="field-hint">{{ t('agentSettings.redirectHostsHint') }}</small>
        </div>
      </div>
      <div v-if="canWrite">
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
      </div>
    </form>

    <template v-if="canReadLog">
      <h2 class="panel-title">{{ t('agentSettings.calls') }}</h2>
      <AgentCallTable scope="all" />
    </template>
  </div>
</template>

<style scoped lang="scss">
.agents-form {
  display: grid;
  gap: var(--space-3);
}

.section-title {
  margin: var(--space-3) 0 0;
  font-family: var(--font-head);
}

.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}
</style>
