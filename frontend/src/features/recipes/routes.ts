import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'

import { Permission } from '@/core/auth/permissions'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const writers = [Permission.WRITE_RECIPES, Permission.MANAGE_RECIPES]

// A signed-in reader gets the full recipe pages instead of the public ones.
function toFullPages(to: RouteLocationNormalized) {
  if (!useCurrentUserStore().isSignedIn) return true
  return to.name === 'public-recipe'
    ? { name: 'recipe', params: { id: to.params.id } }
    : { name: 'recipes' }
}

export default [
  {
    path: '/recipes',
    name: 'recipes',
    component: () => import('@/features/recipes/views/RecipesView.vue'),
    meta: { title: 'nav.recipes' },
  },
  {
    path: '/recipes/new',
    name: 'recipe-new',
    component: () => import('@/features/recipes/views/RecipeEditorView.vue'),
    meta: { title: 'recipes.editor.newTitle', permissions: [Permission.WRITE_RECIPES] },
  },
  {
    path: '/recipes/drafts',
    name: 'recipe-drafts',
    component: () => import('@/features/recipes/views/DraftsView.vue'),
    meta: { title: 'recipes.drafts.title', permissions: writers },
  },
  {
    path: '/recipes/:id',
    name: 'recipe',
    component: () => import('@/features/recipes/views/RecipeView.vue'),
    meta: { title: 'nav.recipes' },
  },
  {
    path: '/recipes/:id/edit',
    name: 'recipe-edit',
    component: () => import('@/features/recipes/views/RecipeEditorView.vue'),
    meta: { title: 'recipes.editor.editTitle', permissions: writers },
  },
  {
    path: '/recipes/:id/variations/new',
    name: 'recipe-variation-new',
    component: () => import('@/features/recipes/views/VariationEditorView.vue'),
    meta: { title: 'recipes.variations.editor.newTitle', permissions: [Permission.WRITE_RECIPES] },
  },
  {
    path: '/recipes/:id/variations/:variationId/edit',
    name: 'recipe-variation-edit',
    component: () => import('@/features/recipes/views/VariationEditorView.vue'),
    meta: { title: 'recipes.variations.editor.editTitle', permissions: [Permission.WRITE_RECIPES] },
  },
  {
    path: '/recipes/:id/cook',
    name: 'recipe-cook',
    component: () => import('@/features/recipes/views/CookModeView.vue'),
    meta: { layout: 'fullscreen', title: 'recipes.cookMode.title' },
  },
  {
    path: '/public',
    redirect: { name: 'public-recipes' },
  },
  {
    path: '/public/recipes',
    name: 'public-recipes',
    component: () => import('@/features/recipes/views/PublicRecipesView.vue'),
    meta: { layout: 'guest', requiresAuth: false, title: 'recipes.public.title' },
    beforeEnter: toFullPages,
  },
  {
    path: '/public/recipes/:id',
    name: 'public-recipe',
    component: () => import('@/features/recipes/views/PublicRecipeView.vue'),
    meta: { layout: 'guest', requiresAuth: false, title: 'recipes.public.title' },
    beforeEnter: toFullPages,
  },
] satisfies RouteRecordRaw[]
