<script setup lang="ts">
/**
 * A person as a picker row, a chosen value or a chip: the avatar (or the
 * initials) next to the display name. `size` picks the small avatar of a
 * chip or the larger one of a suggestion row.
 */
import UserAvatar from '@/shared/components/UserAvatar.vue'

withDefaults(
  defineProps<{ name: string; avatarId?: string | null; size?: 'small' | 'normal' }>(),
  { avatarId: null, size: 'normal' },
)
</script>

<template>
  <span class="person-option" :class="`person-option--${size}`">
    <UserAvatar :name="name" :avatar-id="avatarId" class="person-option-avatar" />
    <span class="person-option-name">{{ name }}</span>
  </span>
</template>

<style scoped lang="scss">
.person-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.person-option--normal {
  --avatar-size: 1.75rem;
}

.person-option--small {
  --avatar-size: 1.25rem;

  gap: var(--space-1);
}

.person-option-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
