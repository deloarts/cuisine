<script setup lang="ts">
/**
 * Adds every ingredient of one recipe, scaled to the chosen servings. The
 * recipe's sub-recipes can each be marked "I'll buy it" and then go on the
 * list as one item instead of their ingredients.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import BoughtSubRecipes from '@/shared/cookbook/BoughtSubRecipes.vue'
import RecipePicker from '@/shared/cookbook/RecipePicker.vue'
import { subRecipeChoices, type SubRecipeNeed } from '@/shared/cookbook/subRecipes'
import type { RecipeSummaryResponse } from '@/shared/cookbook/types'
import { getRecipe } from '@/features/shopping/api/shopping'

export interface AddRecipeValue {
  recipe_id: string
  servings: number
  bought_sub_recipe_ids: string[]
}

defineProps<{ saving: boolean }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ submit: [value: AddRecipeValue] }>()

const { t } = useI18n()
const recipe = ref<RecipeSummaryResponse | null>(null)
const servings = ref(2)
const needs = ref<SubRecipeNeed[]>([])
const bought = ref<string[]>([])

const choices = computed(() =>
  recipe.value && typeof recipe.value === 'object'
    ? subRecipeChoices([{ id: recipe.value.id, title: recipe.value.title, needs: needs.value }])
    : [],
)

watch(recipe, async (r) => {
  needs.value = []
  bought.value = []
  if (!r || typeof r !== 'object') return
  servings.value = r.base_servings
  try {
    const detail = await getRecipe(r.id)
    if (recipe.value === r) needs.value = detail.needs
  } catch {
    // Without the detail the recipe is simply added in full.
    needs.value = []
  }
})

function onShow() {
  recipe.value = null
  servings.value = 2
}

function submit() {
  if (!recipe.value || typeof recipe.value !== 'object') return
  emit('submit', { recipe_id: recipe.value.id, servings: servings.value, bought_sub_recipe_ids: bought.value })
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('shopping.addRecipe')" class="recipe-dialog" @show="onShow">
    <form class="recipe-form" @submit.prevent="submit">
      <div class="field">
        <label for="add-recipe">{{ t('shopping.recipe') }}</label>
        <RecipePicker v-model="recipe" input-id="add-recipe" :placeholder="t('shopping.recipeSearch')" />
      </div>
      <div class="field">
        <label for="add-recipe-servings">{{ t('shopping.servings') }}</label>
        <InputNumber v-model="servings" input-id="add-recipe-servings" :min="1" :max="99" show-buttons fluid />
      </div>
      <BoughtSubRecipes v-model="bought" :choices="choices" id-prefix="add-recipe-bought" />
      <div class="recipe-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('shopping.add')" icon="mdi mdi-cart-plus" :loading="saving" :disabled="!recipe" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.recipe-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.recipe-form {
  display: grid;
  gap: var(--space-3);
}

.recipe-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
