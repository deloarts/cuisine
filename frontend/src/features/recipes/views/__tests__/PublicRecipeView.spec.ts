import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { PublicRecipeDetail, PublicRecipePage } from '@/features/recipes/api/publicRecipes'
import PublicRecipeView from '@/features/recipes/views/PublicRecipeView.vue'
import PublicRecipesView from '@/features/recipes/views/PublicRecipesView.vue'

const getPublicRecipe = vi.fn<(id: string, options?: { servings?: number }) => Promise<PublicRecipeDetail>>()
const listPublicRecipes = vi.fn<() => Promise<PublicRecipePage>>()

vi.mock('@/features/recipes/api/publicRecipes', () => ({
  getPublicRecipe: (id: string, options?: { servings?: number }) => getPublicRecipe(id, options),
  listPublicRecipes: () => listPublicRecipes(),
  listPublicTags: () => Promise.resolve([{ id: 't1', kind: 'course', name: 'Soup', color: null }]),
  publicImageUrl: (recipeId: string, imageId: string) => `/public-image/${recipeId}/${imageId}`,
}))

const ZERO = '00000000-0000-0000-0000-000000000000'
const unit = { kind: 'mass', name: 'gram', plural_name: 'grams', abbreviation: 'g' }

function recipe(): PublicRecipeDetail {
  return {
    id: 'r1',
    title: 'Lasagne',
    description: 'Layered',
    description_text: 'Layered',
    locale: 'en-GB',
    available_locales: ['en-GB'],
    cover_image_id: 'img1',
    base_servings: 2,
    prep_minutes: 10,
    cook_minutes: 20,
    rest_minutes: null,
    total_minutes: 30,
    difficulty: 'easy',
    tags: [],
    allergens: ['gluten'],
    diets: ['vegetarian'],
    season_months: [],
    in_season: false,
    author: null,
    author_avatar: false,
    published_at: null,
    tips: '',
    yield_amount: null,
    yield_unit: null,
    servings: 2,
    ingredients: [{ name: 'Flour', amount: 200, unit, note: '', sub_recipe: null }],
    needs: [
      {
        sub_recipe: { id: null, title: null, accessible: false, cover_image_id: null },
        amount: null,
        unit: null,
        batches: 1,
      },
      {
        sub_recipe: { id: 'r2', title: 'Pasta sheets', accessible: true, cover_image_id: null },
        amount: null,
        unit: null,
        batches: 1,
      },
    ],
    equipment: [],
    steps: [
      {
        position: 1,
        text: `Spread the @[?](recipe:${ZERO}) over the @[Flour](ingredient:${ZERO})`,
        duration_minutes: null,
        image_id: null,
        ingredients: [
          {
            name: '',
            amount: null,
            unit: null,
            note: '',
            sub_recipe: { id: null, title: null, accessible: false, cover_image_id: null },
          },
        ],
        equipment: [],
      },
    ],
    nutrition: {
      total: { kcal: 700 },
      per_serving: { kcal: 350 },
      complete: true,
      extended: [],
    },
    source_name: null,
    source_url: null,
  }
}

async function mountView(path: string, component: object) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/public/recipes', name: 'public-recipes', component: PublicRecipesView },
      { path: '/public/recipes/:id', name: 'public-recipe', component: PublicRecipeView },
      { path: '/login', name: 'login', component: { template: '<div>login</div>' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(component, { global: { plugins: [router, i18n, OpenVue] } })
  await flushPromises()
  return wrapper
}

describe('PublicRecipeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('shows the recipe with placeholders for hidden sub-recipes and nothing to take away', async () => {
    getPublicRecipe.mockResolvedValue(recipe())
    const wrapper = await mountView('/public/recipes/r1', PublicRecipeView)

    expect(wrapper.text()).toContain('Lasagne')
    expect(wrapper.text()).toContain('200 g')
    expect(wrapper.text()).toContain('Pasta sheets')
    expect(wrapper.text()).toContain('a recipe that is not public')
    expect(wrapper.text()).not.toContain('?')
    expect(wrapper.find('img').attributes('src')).toBe('/public-image/r1/img1')
    // The print note is there for paper; there is no button to print,
    // export or download.
    expect(wrapper.find('[data-testid="public-print-note"]').text()).toBe('Sign in to print this recipe.')
    const labels = wrapper.findAll('button').map((b) => b.text().toLowerCase())
    expect(labels.some((l) => /print|export|download/.test(l))).toBe(false)
    expect(wrapper.find('a[href^="/recipes/"]').exists()).toBe(false)
  })

  it('says so when the recipe is not public', async () => {
    getPublicRecipe.mockRejectedValue({ isAxiosError: true, response: { status: 404 } })
    const wrapper = await mountView('/public/recipes/r9', PublicRecipeView)
    expect(wrapper.text()).toContain('This recipe is not public, or not any more.')
  })
})

describe('PublicRecipesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('lists the public recipes with the display-size cover', async () => {
    const { id, title, description_text, locale, available_locales, cover_image_id } = recipe()
    listPublicRecipes.mockResolvedValue({
      items: [
        {
          ...recipe(),
          id,
          title,
          description_text,
          locale,
          available_locales,
          cover_image_id,
          author: 'Anna Cook',
        },
      ],
      total: 1,
    })
    const wrapper = await mountView('/public/recipes', PublicRecipesView)
    expect(wrapper.text()).toContain('Lasagne')
    expect(wrapper.text()).toContain('by Anna Cook')
    expect(wrapper.text()).toContain('Soup')
    expect(wrapper.find('img').attributes('src')).toBe('/public-image/r1/img1')
  })
})
