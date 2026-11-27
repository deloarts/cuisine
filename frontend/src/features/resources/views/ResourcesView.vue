<script setup lang="ts">
/**
 * The shared catalogue resources: tags, units, ingredient categories,
 * families and kitchen equipment, one tab each with the active tab in the URL (`/resources/:tab?`).
 * Switching tabs drops the previous tab's filters from the query. Each tab
 * is a management table that fills the page and shows the tab list at the
 * top of its card through its `tabs` slot. The page header's button creates
 * an item of the active tab through the `create` function every tab exposes.
 */
import { computed, onMounted, ref, watch, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import PageHeader from '@/shared/components/PageHeader.vue'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import CategoriesTab from '@/features/resources/components/CategoriesTab.vue'
import EquipmentTab from '@/features/resources/components/EquipmentTab.vue'
import FamiliesTab from '@/features/resources/components/FamiliesTab.vue'
import TagsTab from '@/features/resources/components/TagsTab.vue'
import UnitsTab from '@/features/resources/components/UnitsTab.vue'
import { useResourceUsage } from '@/features/resources/components/useResourceUsage'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const TABS: { value: string; component: Component }[] = [
  { value: 'tags', component: TagsTab },
  { value: 'units', component: UnitsTab },
  { value: 'categories', component: CategoriesTab },
  { value: 'families', component: FamiliesTab },
  { value: 'equipment', component: EquipmentTab },
]

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()
const usage = useResourceUsage()
const canWrite = computed(() => currentUser.hasPermission(Permission.WRITE_RESOURCES))

const requested = computed(() => (typeof route.params.tab === 'string' ? route.params.tab : ''))
const active = computed({
  get: () => (TABS.some((tab) => tab.value === requested.value) ? requested.value : TABS[0]!.value),
  set: (value: string) => void router.push({ name: 'resources', params: { tab: value } }),
})
const current = computed(() => TABS.find((tab) => tab.value === active.value)!)

// The mounted tab; every tab exposes `create`, which opens its empty dialog.
const tab = ref<{ create: () => void } | null>(null)

watch(
  requested,
  () => {
    if (requested.value && requested.value !== active.value) {
      void router.replace({ name: 'resources', params: { tab: active.value } })
    }
  },
  { immediate: true },
)

onMounted(() => {
  resources.load().catch((err: unknown) => toast.error(err))
  usage.reload().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <section class="table-page">
    <PageHeader :title="t('nav.resources')">
      <Button
        v-if="canWrite"
        :label="t(`resources.${active}.create`)"
        icon="mdi mdi-plus"
        @click="tab?.create()"
      />
    </PageHeader>
    <p v-if="!canWrite" class="hint">{{ t('resources.readOnly') }}</p>
    <component :is="current.component" :key="current.value" ref="tab" :can-write="canWrite">
      <template #tabs>
        <Tabs v-model:value="active" scrollable>
          <TabList class="card-tabs">
            <Tab v-for="item in TABS" :key="item.value" :value="item.value">{{ t(`resources.tabs.${item.value}`) }}</Tab>
          </TabList>
        </Tabs>
      </template>
    </component>
  </section>
</template>
