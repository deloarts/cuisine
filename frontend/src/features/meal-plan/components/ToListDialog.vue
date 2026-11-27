<script setup lang="ts">
/**
 * Sends the shopping for the shown week to one of the user's lists. The
 * sub-recipes of the planned recipes can be marked "I'll buy it", so they go
 * on the list as one item each instead of their ingredients.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BoughtSubRecipes from '@/shared/cookbook/BoughtSubRecipes.vue'
import { subRecipeChoices, type RecipeNeeds, type SubRecipeChoice } from '@/shared/cookbook/subRecipes'
import { getRecipe, listShoppingLists, type ShoppingListSummary } from '@/features/meal-plan/api/mealPlan'
import { useAppToast } from '@/core/composables/useAppToast'

export interface ToListValue {
  listId: string
  bought: string[]
  choices: SubRecipeChoice[]
}

const props = defineProps<{ saving: boolean; recipes: { id: string; title: string }[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ submit: [value: ToListValue] }>()

const { t } = useI18n()
const toast = useAppToast()
const lists = ref<ShoppingListSummary[]>([])
const listId = ref<string | null>(null)
const needs = ref<RecipeNeeds[]>([])
const bought = ref<string[]>([])
const choices = computed(() => subRecipeChoices(needs.value))

async function loadNeeds() {
  const unique = [...new Map(props.recipes.map((r) => [r.id, r])).values()]
  const details = await Promise.all(
    unique.map(async (r) => {
      try {
        const detail = await getRecipe(r.id)
        return { id: r.id, title: detail.title, needs: detail.needs }
      } catch {
        // A recipe that cannot be read is simply added in full.
        return { id: r.id, title: r.title, needs: [] }
      }
    }),
  )
  needs.value = details
}

async function onShow() {
  bought.value = []
  needs.value = []
  try {
    lists.value = await listShoppingLists()
    listId.value = lists.value[0]?.id ?? null
  } catch (err) {
    toast.error(err)
  }
  await loadNeeds()
}

function submit() {
  if (listId.value) emit('submit', { listId: listId.value, bought: bought.value, choices: choices.value })
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('mealPlan.toList')" class="to-list-dialog" @show="onShow">
    <form class="to-list-form" @submit.prevent="submit">
      <p class="hint">{{ t('mealPlan.toListHint') }}</p>
      <div v-if="lists.length" class="field">
        <label id="to-list-label" for="to-list">{{ t('mealPlan.list') }}</label>
        <Select
          id="to-list"
          v-model="listId"
          :options="lists"
          option-label="name"
          option-value="id"
          aria-labelledby="to-list-label"
          fluid
        />
      </div>
      <p v-else class="empty-note">
        {{ t('mealPlan.noLists') }}
        <RouterLink :to="{ name: 'shopping' }">{{ t('mealPlan.createList') }}</RouterLink>
      </p>
      <BoughtSubRecipes v-model="bought" :choices="choices" id-prefix="to-list-bought" show-recipes />
      <div class="to-list-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('mealPlan.send')" icon="mdi mdi-cart-arrow-down" :loading="saving" :disabled="!listId" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.to-list-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.to-list-form {
  display: grid;
  gap: var(--space-3);
}

.to-list-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
