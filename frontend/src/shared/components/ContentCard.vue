<script setup lang="ts">
/**
 * The card every page builds its panels from: the content surface with its
 * border, radius and the shared inner padding (`--card-padding`, defined
 * with the `.card` style in `assets/styles/main.scss`). `as` renders it as
 * another element where the markup needs one (a `section`, `form`, `li` or
 * `ul`); classes, attributes and listeners pass through to that element.
 */
withDefaults(defineProps<{ as?: string }>(), { as: 'div' })
</script>

<template>
  <component :is="as" class="card"><slot /></component>
</template>
