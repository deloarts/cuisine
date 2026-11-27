<script setup lang="ts">
/**
 * The average rating and the reader's own stars and comment, of the recipe
 * itself or, with `variationId`, of one of its variations.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { rateRecipe, removeRating } from '@/features/recipes/api/recipes'

const props = defineProps<{
  recipeId: string
  average: number | null
  count: number
  own: { stars: number; comment: string } | null
  variationId?: string | null
}>()
const emit = defineEmits<{ changed: [average: number | null, count: number, own: boolean] }>()

const { t } = useI18n()
const toast = useAppToast()

const stars = ref(props.own?.stars ?? 0)
const comment = ref(props.own?.comment ?? '')
const saving = ref(false)

watch(
  () => props.own,
  (own) => {
    stars.value = own?.stars ?? 0
    comment.value = own?.comment ?? ''
  },
)

async function save() {
  if (stars.value < 1) return
  saving.value = true
  try {
    const result = await rateRecipe(props.recipeId, stars.value, comment.value.trim(), props.variationId ?? null)
    emit('changed', result.rating_average, result.rating_count, true)
    toast.success(t('recipes.rating.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function remove() {
  saving.value = true
  try {
    const result = await removeRating(props.recipeId, props.variationId ?? null)
    stars.value = 0
    comment.value = ''
    emit('changed', result.rating_average, result.rating_count, false)
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="rating">
    <p class="rating-average">
      <template v-if="average !== null">
        <span class="mdi mdi-star" aria-hidden="true" />
        {{ t('recipes.rating.average', { avg: average.toFixed(1), count }, count) }}
      </template>
      <template v-else>{{ t('recipes.rating.none') }}</template>
    </p>
    <div class="field">
      <span id="rating-stars-label" class="field-label">{{ t('recipes.rating.yours') }}</span>
      <Rating v-model="stars" :cancel="false" aria-labelledby="rating-stars-label" />
    </div>
    <div class="field">
      <label for="rating-comment" class="field-label">{{ t('recipes.rating.comment') }}</label>
      <Textarea id="rating-comment" v-model="comment" rows="2" auto-resize fluid />
    </div>
    <div class="row-actions">
      <Button
        v-if="own"
        :label="t('recipes.rating.remove')"
        text
        severity="secondary"
        :disabled="saving"
        @click="remove"
      />
      <Button
        :label="t('recipes.rating.save')"
        :disabled="stars < 1"
        :loading="saving"
        @click="save"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.rating {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.rating-average {
  font-weight: 700;

  .mdi {
    color: var(--p-yellow-500);
  }
}
</style>
