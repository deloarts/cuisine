<script setup lang="ts">
/**
 * A recipe's tags as links to the recipe list filtered by each tag. The list
 * keeps to one line: the tags that fit stay, the rest wait behind a "+N"
 * chip, and clicking that chip shows every tag on as many lines as they need.
 * The line is measured again whenever the list changes its width.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ tags: { id: string; name: string }[] }>()

const { t } = useI18n()
const list = ref<HTMLElement | null>(null)
const moreItem = ref<HTMLElement | null>(null)
const shown = ref(props.tags.length)
const expanded = ref(false)
let run = 0
let width = -1
let observer: ResizeObserver | undefined

// Shows every tag, finds the first one that wraps, then drops tags from the
// end until the chip also fits on the first line. One tag always stays.
async function fit() {
  const current = ++run
  shown.value = props.tags.length
  if (expanded.value) return
  await nextTick()
  const items = Array.from(list.value?.querySelectorAll<HTMLElement>('[data-tag]') ?? [])
  if (current !== run || !items.length) return
  const top = items[0]!.offsetTop
  let n = items.findIndex((el) => el.offsetTop > top)
  if (n === -1) return
  for (;;) {
    shown.value = n
    await nextTick()
    if (current !== run) return
    if (n <= 1 || !moreItem.value || moreItem.value.offsetTop <= top) return
    n -= 1
  }
}

function expand() {
  expanded.value = true
  run += 1
  shown.value = props.tags.length
}

watch(() => props.tags, fit)

onMounted(() => {
  void fit()
  if (typeof ResizeObserver === 'undefined' || !list.value) return
  observer = new ResizeObserver(([entry]) => {
    if (!entry || entry.contentRect.width === width) return
    width = entry.contentRect.width
    void fit()
  })
  observer.observe(list.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <ul ref="list" class="recipe-tags" data-testid="recipe-tags">
    <li v-for="tag in tags.slice(0, shown)" :key="tag.id" data-tag>
      <RouterLink :to="{ name: 'recipes', query: { tag: tag.id } }">{{ tag.name }}</RouterLink>
    </li>
    <li v-if="shown < tags.length" ref="moreItem">
      <button type="button" aria-expanded="false" data-testid="recipe-tags-more" @click="expand">
        {{ t('recipes.detail.moreTags', { n: tags.length - shown }) }}
      </button>
    </li>
  </ul>
</template>

<style scoped lang="scss">
.recipe-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;

  a,
  button {
    display: inline-flex;
    align-items: center;
    min-height: 2rem;
    padding: 0 var(--space-3);
    border: 0;
    border-radius: 2rem;
    background: var(--p-surface-100);
    color: inherit;
    text-decoration: none;
    font: inherit;
    font-size: var(--font-size-sm);
  }

  button {
    cursor: pointer;
    color: var(--p-text-muted-color);

    &:focus-visible {
      outline: 2px solid var(--p-primary-color);
      outline-offset: 2px;
    }
  }
}

.p-dark .recipe-tags {
  a,
  button {
    background: var(--p-surface-800);
  }
}
</style>
