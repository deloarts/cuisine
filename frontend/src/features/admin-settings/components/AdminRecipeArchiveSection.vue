<script setup lang="ts">
/**
 * Moving many recipes between Cuisine instances: the export packs recipes
 * (all the admin can see, or the chosen ones) with their sub-recipes, the
 * catalogue entries they use and their images into one `.cui` file; the
 * import is the same as every cook's (`RecipeImport`), creating each recipe
 * as a draft of the admin or updating their earlier import of it.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { downloadBlob } from '@/shared/composables/fileTransfer'
import RecipeImport from '@/shared/cookbook/RecipeImport.vue'
import RecipePicker from '@/shared/cookbook/RecipePicker.vue'
import type { RecipeSummaryResponse } from '@/shared/cookbook/types'
import { adminApi } from '@/features/admin-settings/api/admin'
import { useAppToast } from '@/core/composables/useAppToast'

const { t } = useI18n()
const toast = useAppToast()

const scope = ref<'all' | 'chosen'>('all')
const chosen = ref<RecipeSummaryResponse[]>([])
const picked = ref<RecipeSummaryResponse | null>(null)
const exporting = ref(false)

const canExport = computed(() => scope.value === 'all' || chosen.value.length > 0)

function addPicked(value: RecipeSummaryResponse | string | null) {
  if (value && typeof value === 'object' && !chosen.value.some((r) => r.id === value.id)) {
    chosen.value = [...chosen.value, value]
  }
  picked.value = null
}

function removeChosen(id: string) {
  chosen.value = chosen.value.filter((r) => r.id !== id)
}

async function exportArchive() {
  exporting.value = true
  try {
    const ids = scope.value === 'chosen' ? chosen.value.map((r) => r.id) : undefined
    const data = await adminApi.exportRecipes(ids ? { recipe_id: ids } : {})
    const day = new Date().toISOString().slice(0, 10)
    downloadBlob(data, `cuisine-recipes-${day}.cui`)
  } catch (err) {
    toast.error(err)
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <section class="settings-tab">
    <h2 class="panel-title">{{ t('recipeArchive.title') }}</h2>
    <p class="hint">{{ t('recipeArchive.hint') }}</p>

    <div class="block">
      <h3 class="block-title">{{ t('recipeArchive.exportTitle') }}</h3>
      <div class="choice">
        <RadioButton v-model="scope" input-id="archive-all" value="all" />
        <label for="archive-all">{{ t('recipeArchive.all') }}</label>
      </div>
      <div class="choice">
        <RadioButton v-model="scope" input-id="archive-chosen" value="chosen" />
        <label for="archive-chosen">{{ t('recipeArchive.chosen') }}</label>
      </div>
      <div v-if="scope === 'chosen'" class="field nested">
        <label for="archive-recipe">{{ t('recipeArchive.addRecipe') }}</label>
        <RecipePicker
          v-model="picked"
          input-id="archive-recipe"
          :placeholder="t('recipeArchive.search')"
          @update:model-value="addPicked"
        />
        <div v-if="chosen.length" class="chips">
          <Chip
            v-for="r in chosen"
            :key="r.id"
            :label="r.title"
            removable
            :remove-icon="'mdi mdi-close'"
            @remove="removeChosen(r.id)"
          />
        </div>
      </div>
      <div>
        <Button
          :label="t('recipeArchive.export')"
          icon="mdi mdi-archive-arrow-down-outline"
          :loading="exporting"
          :disabled="!canExport"
          @click="exportArchive"
        />
      </div>
    </div>

    <div class="block">
      <h3 class="block-title">{{ t('recipeArchive.importTitle') }}</h3>
      <p class="hint">{{ t('recipeArchive.importHint') }}</p>
      <RecipeImport outlined />
    </div>
  </section>
</template>

<style scoped lang="scss">
.block {
  display: grid;
  gap: var(--space-2);
}

.block-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.choice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.nested {
  max-width: 32rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
</style>
