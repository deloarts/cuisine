<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import SecurityEventTable from '@/shared/components/SecurityEventTable.vue'

const { t } = useI18n()
</script>

<template>
  <div class="settings-tab">
    <h2 class="panel-title">{{ t('account.activity.title') }}</h2>
    <p class="hint">{{ t('account.activity.hint') }}</p>
    <SecurityEventTable scope="own" />
  </div>
</template>
