<script setup lang="ts">
/**
 * A round avatar: the user's uploaded image when they have one, otherwise
 * up to two initials of their name. An image that fails to load falls back
 * to the initials too. Signed-in pages pass the stored file's `avatarId`;
 * the public pages pass the `src` of their own route. The size and colours
 * come from the parent through `--avatar-size`, `--avatar-background` and
 * `--avatar-color`. The avatar is decorative, since a name always stands
 * next to it, so the initials are drawn by CSS and add no text.
 */
import { computed, ref, watch } from 'vue'

import { imageUrl } from '@/shared/components/recipes/recipeImage'

const props = defineProps<{ name: string; avatarId?: string | null; src?: string | null }>()

const failed = ref(false)
watch(
  () => [props.avatarId, props.src],
  () => {
    failed.value = false
  },
)

const imageSrc = computed(() => {
  if (failed.value) return null
  return props.src ?? (props.avatarId ? imageUrl(props.avatarId) : null)
})
const initials = computed(
  () =>
    props.name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('') || '?',
)
</script>

<template>
  <span class="user-avatar">
    <img v-if="imageSrc" :src="imageSrc" alt="" class="user-avatar-image" @error="failed = true" />
    <span v-else class="user-avatar-initials" :data-initials="initials" aria-hidden="true" />
  </span>
</template>

<style scoped lang="scss">
.user-avatar {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: var(--avatar-size, 2.2rem);
  height: var(--avatar-size, 2.2rem);
  overflow: hidden;
  border-radius: 50%;
  background: var(--avatar-background, var(--p-primary-700));
  color: var(--avatar-color, var(--p-primary-contrast-color));
  font-family: var(--font-head);
  font-weight: 700;
  font-size: calc(var(--avatar-size, 2.2rem) * 0.4);
}

.user-avatar-initials::before {
  content: attr(data-initials);
}

.user-avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
