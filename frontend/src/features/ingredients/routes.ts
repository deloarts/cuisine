import type { RouteRecordRaw } from 'vue-router'

import { Permission } from '@/core/auth/permissions'

export default [
  {
    path: '/ingredients',
    name: 'ingredients',
    component: () => import('@/features/ingredients/views/IngredientsView.vue'),
    meta: { title: 'nav.ingredients' },
  },
  {
    path: '/ingredients/new',
    name: 'ingredient-new',
    component: () => import('@/features/ingredients/views/IngredientEditView.vue'),
    meta: { title: 'ingredients.create', permissions: [Permission.WRITE_INGREDIENTS] },
  },
  {
    path: '/ingredients/:id',
    name: 'ingredient',
    component: () => import('@/features/ingredients/views/IngredientEditView.vue'),
    meta: { title: 'nav.ingredients' },
  },
] satisfies RouteRecordRaw[]
