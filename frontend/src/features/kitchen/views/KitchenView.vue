<script setup lang="ts">
/**
 * "My kitchen": the equipment a cook owns, so recipes can say what is
 * missing. In a household the kitchen belongs to the household and every
 * member edits it; otherwise it is the user's own. Nobody else sees it.
 *
 * Until it is set up nothing is flagged. Setting it up opens a checklist of
 * the whole catalogue grouped by kind with the basic items ticked in
 * advance; once set up, every tick saves on its own after a short pause.
 * Built for the phone first: one column of large rows with a search on top.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDebounceFn } from '@vueuse/core'
import { useConfirm } from 'openvue/useconfirm'

import PageHeader from '@/shared/components/PageHeader.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { equipmentIcon } from '@/shared/cookbook/equipment'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  forgetKitchen,
  getKitchen,
  listEquipment,
  saveKitchen,
  setUpKitchen,
  type EquipmentResponse,
  type Kitchen,
} from '@/features/kitchen/api/kitchen'
import { groupByKind, initialSelection } from '@/features/kitchen/kitchen'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()

const kitchen = ref<Kitchen | null>(null)
const catalogue = ref<EquipmentResponse[]>([])
const selected = ref<Set<string>>(new Set())
const query = ref('')
const loading = ref(true)
const setting = ref(false)
const saving = ref(false)
// Set up has started on this page: the checklist shows before the first save.
const choosing = ref(false)

const groups = computed(() => groupByKind(catalogue.value, selected.value, query.value))
const showList = computed(() => kitchen.value?.set_up || choosing.value)
const owner = computed(() =>
  kitchen.value?.household ? t('kitchen.ownerHousehold') : t('kitchen.ownerPersonal'),
)

async function load() {
  loading.value = true
  try {
    const [k, items] = await Promise.all([getKitchen(), listEquipment()])
    kitchen.value = k
    catalogue.value = items
    selected.value = initialSelection(k, items)
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function startSetup() {
  if (!kitchen.value) return
  selected.value = initialSelection({ set_up: false, equipment: [] }, catalogue.value)
  choosing.value = true
}

const persist = useDebounceFn(async () => {
  saving.value = true
  try {
    kitchen.value = await saveKitchen([...selected.value])
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}, 600)

function toggle(id: string, on: boolean) {
  const next = new Set(selected.value)
  if (on) next.add(id)
  else next.delete(id)
  selected.value = next
  if (kitchen.value?.set_up) void persist()
}

async function finishSetup() {
  setting.value = true
  try {
    kitchen.value = await setUpKitchen([...selected.value])
    choosing.value = false
    toast.success(t('kitchen.ready'))
  } catch (err) {
    toast.error(err)
  } finally {
    setting.value = false
  }
}

function forget() {
  confirm.require({
    message: t('kitchen.forgetConfirm'),
    header: t('common.confirm'),
    acceptProps: { label: t('kitchen.forget'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void (async () => {
        try {
          await forgetKitchen()
          choosing.value = false
          await load()
        } catch (err) {
          toast.error(err)
        }
      })()
    },
  })
}

function count(items: EquipmentResponse[]): number {
  return items.filter((item) => selected.value.has(item.id)).length
}

onMounted(() => void load())
</script>

<template>
  <section class="kitchen">
    <PageHeader :title="t('nav.myKitchen')" />

    <SkeletonRegion v-if="loading" class="kitchen" :label="t('kitchen.loading')" testid="kitchen-skeleton">
      <div class="kitchen-owner">
        <Skeleton width="7rem" height="1.75rem" border-radius="1rem" />
        <Skeleton width="14rem" height="0.875rem" />
      </div>
      <div class="kitchen-bar">
        <Skeleton height="2.75rem" />
      </div>
      <div class="kitchen-groups">
        <ContentCard v-for="g in 2" :key="g" class="kitchen-group">
          <div class="kitchen-group-title">
            <Skeleton width="8rem" height="1.25rem" />
            <Skeleton width="2.5rem" height="0.875rem" />
          </div>
          <ul class="kitchen-list">
            <li v-for="n in 5" :key="n" class="kitchen-item">
              <Skeleton size="1.25rem" />
              <Skeleton size="1.5rem" shape="circle" />
              <Skeleton :width="n % 2 ? '45%' : '60%'" />
            </li>
          </ul>
        </ContentCard>
      </div>
    </SkeletonRegion>

    <template v-else-if="kitchen">
      <p class="kitchen-owner">
        <Tag :value="owner" :icon="kitchen.household ? 'mdi mdi-home-heart' : 'mdi mdi-account'" severity="secondary" />
        <span class="hint">{{ kitchen.household ? t('kitchen.householdHint') : t('kitchen.personalHint') }}</span>
      </p>

      <ContentCard v-if="!showList" class="kitchen-intro">
        <i class="mdi mdi-stove kitchen-intro-icon" aria-hidden="true" />
        <h2 class="kitchen-intro-title">{{ t('kitchen.introTitle') }}</h2>
        <p>{{ t('kitchen.introText') }}</p>
        <Button :label="t('kitchen.start')" icon="mdi mdi-playlist-check" @click="startSetup" />
      </ContentCard>

      <template v-else>
        <Message v-if="!kitchen.set_up" severity="info" :closable="false">{{ t('kitchen.setupHint') }}</Message>
        <div class="kitchen-bar">
          <IconField class="kitchen-search">
            <InputIcon class="mdi mdi-magnify" />
            <InputText v-model="query" :placeholder="t('kitchen.search')" :aria-label="t('kitchen.search')" fluid />
          </IconField>
          <span class="text-muted kitchen-count" aria-live="polite">
            {{ t('kitchen.count', { count: selected.size }, selected.size) }}
            <template v-if="saving"> · {{ t('kitchen.saving') }}</template>
          </span>
        </div>

        <p v-if="!groups.length" class="empty-note">{{ t('kitchen.noMatch') }}</p>
        <div class="kitchen-groups">
          <ContentCard as="section" v-for="group in groups" :key="group.kind" class="kitchen-group">
            <h2 class="kitchen-group-title">
              {{ t(`equipmentKinds.${group.kind}`) }}
              <small class="text-muted">{{ count(group.items) }} / {{ group.items.length }}</small>
            </h2>
            <ul class="kitchen-list">
              <li v-for="item in group.items" :key="item.id">
                <label class="kitchen-item" :for="`kitchen-${item.id}`">
                  <Checkbox
                    :model-value="selected.has(item.id)"
                    :input-id="`kitchen-${item.id}`"
                    binary
                    @update:model-value="toggle(item.id, $event)"
                  />
                  <i :class="equipmentIcon(item.icon)" class="kitchen-item-icon" aria-hidden="true" />
                  <span class="kitchen-item-name">{{ item.name }}</span>
                  <small v-if="item.basic" class="text-muted">{{ t('kitchen.basic') }}</small>
                </label>
              </li>
            </ul>
          </ContentCard>
        </div>

        <div v-if="!kitchen.set_up" class="kitchen-actions kitchen-sticky">
          <Button :label="t('common.cancel')" text @click="choosing = false" />
          <Button
            :label="t('kitchen.finish', { count: selected.size })"
            icon="mdi mdi-check"
            :loading="setting"
            @click="finishSetup"
          />
        </div>
        <div v-else class="kitchen-actions">
          <Button :label="t('kitchen.forget')" icon="mdi mdi-restore" text severity="secondary" @click="forget" />
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped lang="scss">
.kitchen {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.kitchen-owner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
}

.kitchen-intro {
  display: grid;
  gap: var(--space-3);
  justify-items: center;
  text-align: center;
}

.kitchen-intro-icon {
  font-size: var(--font-size-4xl);
  color: var(--p-primary-color);
}

.kitchen-intro-title {
  margin: 0;
}

.kitchen-bar {
  display: grid;
  gap: var(--space-2);
}

.kitchen-count {
  font-size: var(--font-size-sm);
}

.kitchen-groups {
  display: grid;
  gap: var(--space-3);
}

.kitchen-group {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
}

.kitchen-group-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: var(--space-1) 0;
  font-family: var(--font-head);
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.kitchen-list {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

.kitchen-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 2.75rem;
  padding: var(--space-1) 0;
  cursor: pointer;
  border-bottom: 1px solid var(--p-content-border-color);
}

.kitchen-list li:last-child .kitchen-item {
  border-bottom: 0;
}

.kitchen-item-icon {
  font-size: var(--font-size-xl);
  color: var(--p-text-muted-color);
}

.kitchen-item-name {
  flex: 1;
}

.kitchen-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

// The set-up button stays in reach under the thumb while the list scrolls,
// above the phone's bottom navigation.
.kitchen-sticky {
  position: sticky;
  bottom: var(--space-2);
  padding: var(--space-2);
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  box-shadow: var(--shadow-sm);
}

@media (min-width: $bp-sm) {
  .kitchen-bar {
    grid-template-columns: minmax(0, 24rem) auto;
    align-items: center;
    justify-content: space-between;
  }

}

@media (min-width: $bp-md) {
  .kitchen-groups {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }
}
</style>
