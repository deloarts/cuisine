<script setup lang="ts">
/**
 * Creates a missing ingredient from inside the recipe editor with just its
 * name, plural and category. Nutrition and conversions are added later on
 * the ingredients page.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { createIngredient, type IngredientResponse } from '@/features/recipes/api/recipes'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ name: string }>()
const emit = defineEmits<{ created: [ingredient: IngredientResponse] }>()

const { t, locale } = useI18n()
const toast = useAppToast()
const resources = useCookbookResources()

const ingredientName = ref('')
const pluralName = ref('')
const categoryId = ref<string | null>(null)
const saving = ref(false)

const categories = computed(() => resources.categories.value)

watch(visible, (open) => {
  if (open) {
    ingredientName.value = props.name
    pluralName.value = ''
    categoryId.value = null
  }
})

onMounted(() => void resources.load().catch(() => undefined))

async function save() {
  if (!ingredientName.value.trim()) return
  saving.value = true
  const original = contentLocaleOf(locale.value)
  try {
    const ingredient = await createIngredient({
      original_locale: original,
      translations: { [original]: { name: ingredientName.value.trim(), plural_name: pluralName.value.trim() } },
      category_id: categoryId.value,
      nutrition_source: 'manual',
    })
    toast.success(t('recipes.editor.ingredientCreated', { name: ingredient.name }))
    emit('created', ingredient)
    visible.value = false
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('recipes.editor.newIngredientTitle')"
    :style="{ width: 'var(--dialog-width-sm)' }"
  >
    <form class="new-ingredient" @submit.prevent="save">
      <div class="field">
        <label for="new-ingredient-name" class="field-label">{{ t('recipes.editor.ingredientName') }}</label>
        <InputText id="new-ingredient-name" v-model="ingredientName" fluid autofocus />
      </div>
      <div class="field">
        <label for="new-ingredient-plural" class="field-label">
          {{ t('recipes.editor.ingredientPlural') }}
        </label>
        <InputText id="new-ingredient-plural" v-model="pluralName" fluid />
      </div>
      <div class="field">
        <label id="new-ingredient-category-label" for="new-ingredient-category" class="field-label">
          {{ t('recipes.editor.ingredientCategory') }}
        </label>
        <Select
          id="new-ingredient-category"
          v-model="categoryId"
          :options="categories"
          option-label="name"
          option-value="id"
          show-clear
          fluid
          aria-labelledby="new-ingredient-category-label"
        />
      </div>
      <p class="hint">{{ t('recipes.editor.ingredientLaterHint') }}</p>
      <div class="row-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button type="submit" :label="t('common.create')" :loading="saving" :disabled="!ingredientName.trim()" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.new-ingredient {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
</style>
