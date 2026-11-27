<script setup lang="ts">
/**
 * Importing a `.cui` file (or an older recipe archive). The file is checked
 * first; when the user imported one of its recipes before, they choose per
 * recipe to update that earlier import or to import a new copy. Every other
 * recipe becomes a new draft. The report follows below.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  importRecipes,
  previewRecipeImport,
  RECIPE_FILE_TYPES,
  type PreviewedRecipe,
  type RecipeImportReport as Report,
} from '@/shared/api/recipeImport'
import { pickFiles } from '@/shared/composables/fileTransfer'
import RecipeImportReport from '@/shared/cookbook/RecipeImportReport.vue'
import ContentCard from '@/shared/components/ContentCard.vue'

withDefaults(defineProps<{ outlined?: boolean }>(), { outlined: false })
const emit = defineEmits<{ imported: [report: Report] }>()

const { t } = useI18n()
const toast = useAppToast()

type Choice = 'update' | 'copy'

const busy = ref(false)
const file = ref<File | null>(null)
const earlier = ref<PreviewedRecipe[]>([])
const others = ref(0)
const choices = ref<Record<string, Choice>>({})
const report = ref<Report | null>(null)

const deciding = computed(() => file.value !== null && earlier.value.length > 0)

async function run(chosen: File, update: string[]) {
  const result = await importRecipes(chosen, update)
  report.value = result
  file.value = null
  earlier.value = []
  toast.success(t('recipeImport.imported', { count: result.recipes.length }, result.recipes.length))
  emit('imported', result)
}

async function pick() {
  const [picked] = await pickFiles(RECIPE_FILE_TYPES)
  if (!picked) return
  busy.value = true
  report.value = null
  try {
    const preview = await previewRecipeImport(picked)
    const matched = preview.recipes.filter((r) => r.earlier)
    if (matched.length === 0) {
      await run(picked, [])
      return
    }
    file.value = picked
    earlier.value = matched
    others.value = preview.recipes.length - matched.length
    choices.value = Object.fromEntries(matched.map((r) => [r.source_id, 'update' as Choice]))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function confirm() {
  if (!file.value) return
  busy.value = true
  try {
    const update = Object.entries(choices.value)
      .filter(([, choice]) => choice === 'update')
      .map(([sourceId]) => sourceId)
    await run(file.value, update)
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

function cancel() {
  file.value = null
  earlier.value = []
}
</script>

<template>
  <div class="recipe-import">
    <div v-if="!deciding">
      <Button
        :label="t('recipeImport.button')"
        icon="mdi mdi-file-import-outline"
        :outlined="outlined"
        severity="secondary"
        :loading="busy"
        @click="pick"
      />
    </div>

    <ContentCard v-else class="decide" role="group" :aria-label="t('recipeImport.decideTitle')">
      <h3 class="decide-title">{{ t('recipeImport.decideTitle') }}</h3>
      <p class="hint">{{ t('recipeImport.decideHint') }}</p>
      <fieldset v-for="r in earlier" :key="r.source_id" class="choice-set">
        <legend>
          <strong>{{ r.title }}</strong>
          <span v-if="r.earlier" class="muted">
            {{ t('recipeImport.earlier', { title: r.earlier.title }) }}
            ({{ t(`recipeImport.status.${r.earlier.status}`) }})
          </span>
        </legend>
        <div class="choice">
          <RadioButton v-model="choices[r.source_id]" :input-id="`update-${r.source_id}`" value="update" />
          <label :for="`update-${r.source_id}`">{{ t('recipeImport.update') }}</label>
        </div>
        <div class="choice">
          <RadioButton v-model="choices[r.source_id]" :input-id="`copy-${r.source_id}`" value="copy" />
          <label :for="`copy-${r.source_id}`">{{ t('recipeImport.copy') }}</label>
        </div>
      </fieldset>
      <p v-if="others" class="hint">{{ t('recipeImport.others', { count: others }, others) }}</p>
      <div class="actions">
        <Button :label="t('recipeImport.confirm')" icon="mdi mdi-check" :loading="busy" @click="confirm" />
        <Button :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="cancel" />
      </div>
    </ContentCard>

    <RecipeImportReport v-if="report" :report="report" />
  </div>
</template>

<style scoped lang="scss">
.recipe-import {
  display: grid;
  gap: var(--space-3);
}

.decide {
  display: grid;
  gap: var(--space-2);
}

.decide-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.choice-set {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  border: 0;

  legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-bottom: var(--space-1);
  }
}

.choice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.muted {
  color: var(--p-text-muted-color);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
