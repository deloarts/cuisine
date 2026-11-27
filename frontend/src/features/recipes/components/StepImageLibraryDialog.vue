<script setup lang="ts">
/**
 * The step image library: photos that steps of other recipes already show,
 * so an interchangeable one, such as chopped onions or a hot pan, is taken
 * once and picked again instead of being photographed for every recipe.
 *
 * Without a search it opens with the photos whose steps share the most of
 * this step's ingredients and equipment; a search looks through step text,
 * recipe titles and ingredient names. The backend offers only images of
 * recipes the cook may see, so picking one never needs another check.
 */
import { watchDebounced } from '@vueuse/core'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { listStepImages, type StepImageResponse } from '@/features/recipes/api/recipes'
import { imageUrl } from '@/shared/components/recipes/recipeImage'

const PAGE = 24

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{
  ingredientIds: string[]
  equipmentIds: string[]
  /** The image the step shows now, marked in the grid. */
  current?: string | null
}>()
const emit = defineEmits<{ pick: [imageId: string] }>()

const { t } = useI18n()
const toast = useAppToast()

const search = ref('')
const items = ref<StepImageResponse[]>([])
const total = ref(0)
const loading = ref(false)
// A slow answer to an earlier search must not replace a newer one.
let request = 0

async function load(append = false) {
  const mine = ++request
  loading.value = true
  try {
    const page = await listStepImages({
      ingredientIds: props.ingredientIds,
      equipmentIds: props.equipmentIds,
      search: search.value.trim(),
      limit: PAGE,
      offset: append ? items.value.length : 0,
    })
    if (mine !== request) return
    items.value = append ? [...items.value, ...page.items] : page.items
    total.value = page.total
  } catch (err) {
    if (mine === request) toast.error(err)
  } finally {
    if (mine === request) loading.value = false
  }
}

watch(visible, (open) => {
  if (!open) return
  search.value = ''
  items.value = []
  void load()
})
watchDebounced(search, () => visible.value && load(), { debounce: 300 })

function pick(item: StepImageResponse) {
  emit('pick', item.image_id)
  visible.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('recipes.editor.library.title')"
    :style="{ width: 'var(--dialog-width-lg)' }"
  >
    <div class="library">
      <p class="hint">{{ t('recipes.editor.library.hint') }}</p>
      <IconField>
        <InputIcon class="mdi mdi-magnify" />
        <InputText
          v-model="search"
          :placeholder="t('recipes.editor.library.search')"
          :aria-label="t('recipes.editor.library.search')"
          fluid
          data-testid="step-image-library-search"
        />
      </IconField>

      <div
        v-if="loading && !items.length"
        class="library-grid"
        role="status"
        :aria-label="t('recipes.loading')"
      >
        <Skeleton v-for="n in 6" :key="n" class="library-skeleton" />
      </div>
      <p v-else-if="!items.length" class="hint" data-testid="step-image-library-empty">
        {{ search.trim() ? t('recipes.editor.library.noMatch') : t('recipes.editor.library.empty') }}
      </p>
      <ul v-else class="library-grid">
        <li v-for="item in items" :key="item.image_id">
          <button
            type="button"
            class="library-item"
            :class="{ 'library-item--current': item.image_id === current }"
            :aria-pressed="item.image_id === current"
            data-testid="step-image-library-item"
            @click="pick(item)"
          >
            <img :src="imageUrl(item.image_id)" alt="" loading="lazy" />
            <span v-if="item.matches" class="library-item-match">
              <span class="mdi mdi-check-decagram-outline" aria-hidden="true" />
              {{ t('recipes.editor.library.matches', { n: item.matches }, item.matches) }}
            </span>
            <span class="library-item-recipe">
              {{ item.recipe.title }} · {{ t('recipes.detail.step', { n: item.step_number }) }}
            </span>
            <span v-if="item.step_text" class="library-item-text">{{ item.step_text }}</span>
          </button>
        </li>
      </ul>

      <Button
        v-if="items.length < total"
        :label="t('recipes.editor.library.more')"
        severity="secondary"
        text
        :loading="loading"
        class="library-more"
        @click="load(true)"
      />
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.library {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.hint {
  margin: 0;
  color: var(--p-text-muted-color);
}

.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.library-skeleton {
  aspect-ratio: 4 / 3;
  height: auto !important;
}

.library-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-1);
  border: 2px solid transparent;
  border-radius: var(--p-border-radius-md);
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:hover {
    background: var(--p-content-hover-background);
  }

  &:focus-visible {
    outline: 2px solid var(--p-primary-color);
    outline-offset: 2px;
  }

  img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    border-radius: var(--p-border-radius-sm);
    background: var(--p-surface-100);
  }
}

.p-dark .library-item img {
  background: var(--p-surface-800);
}

.library-item--current {
  border-color: var(--p-primary-color);
}

.library-item-match {
  color: var(--p-primary-color);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.library-item-recipe {
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.library-item-text {
  display: -webkit-box;
  overflow: hidden;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.library-more {
  align-self: center;
}
</style>
