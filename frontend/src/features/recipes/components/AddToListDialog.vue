<script setup lang="ts">
/**
 * Puts a recipe's ingredients on a shopping list, scaled to the servings
 * chosen on the recipe page. A sub-recipe can be marked "I'll buy it": it
 * then goes on the list as one item instead of its own ingredients.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  addRecipeToList,
  listShoppingLists,
  type SubRecipeNeed,
} from '@/features/recipes/api/recipes'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ recipeId: string; servings: number; needs: SubRecipeNeed[] }>()

const { t } = useI18n()
const toast = useAppToast()

const lists = ref<{ id: string; name: string }[]>([])
const listId = ref<string | null>(null)
const bought = ref<string[]>([])
const saving = ref(false)

// Only sub-recipes the reader can see can be bought instead; a hidden one
// is always expanded into its ingredients.
const buyable = computed(() =>
  props.needs.filter((n) => n.sub_recipe.accessible && n.sub_recipe.id),
)

watch(visible, async (open) => {
  if (!open) return
  bought.value = []
  try {
    const all = await listShoppingLists()
    lists.value = all.map((l) => ({ id: l.id, name: l.name }))
    if (!listId.value || !lists.value.some((l) => l.id === listId.value)) {
      listId.value = lists.value[0]?.id ?? null
    }
  } catch (err) {
    toast.error(err)
  }
})

async function save() {
  if (!listId.value) return
  saving.value = true
  try {
    const result = await addRecipeToList(listId.value, props.recipeId, props.servings, bought.value)
    toast.success(t('recipes.addToList.done', { n: result.added }, result.added))
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
    :header="t('recipes.addToList.title')"
    :style="{ width: 'var(--dialog-width-sm)' }"
  >
    <form class="add-to-list" @submit.prevent="save">
      <p v-if="lists.length === 0" class="hint">{{ t('recipes.addToList.noLists') }}</p>
      <div v-else class="field">
        <span id="add-to-list-label" class="field-label">{{ t('recipes.addToList.list') }}</span>
        <Select
          v-model="listId"
          :options="lists"
          option-label="name"
          option-value="id"
          fluid
          aria-labelledby="add-to-list-label"
        />
      </div>
      <p class="hint">{{ t('recipes.addToList.servings', { n: servings }, servings) }}</p>
      <fieldset v-if="buyable.length" class="add-to-list-bought">
        <legend class="field-label">{{ t('recipes.addToList.buyInstead') }}</legend>
        <div v-for="need in buyable" :key="need.sub_recipe.id!" class="add-to-list-option">
          <Checkbox
            v-model="bought"
            :input-id="`bought-${need.sub_recipe.id}`"
            :value="need.sub_recipe.id"
          />
          <label :for="`bought-${need.sub_recipe.id}`">
            {{ t('recipes.addToList.buyIt', { title: need.sub_recipe.title }) }}
          </label>
        </div>
      </fieldset>
      <div class="row-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button
          type="submit"
          :label="t('recipes.addToList.add')"
          icon="mdi mdi-cart-plus"
          :disabled="!listId"
          :loading="saving"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.add-to-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.add-to-list-bought {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: none;
}

.add-to-list-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}
</style>
