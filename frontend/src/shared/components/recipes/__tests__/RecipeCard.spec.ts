import { mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Schemas } from '@/core/api/generated'
import { i18n } from '@/core/i18n'
import RecipeCard from '@/shared/components/recipes/RecipeCard.vue'

type RecipeSummary = Schemas['RecipeSummaryResponse']

function summary(overrides: Partial<RecipeSummary> = {}): RecipeSummary {
  return {
    id: 'r1',
    title: 'Coq au vin',
    description: '',
    description_text: '',
    locale: 'en-GB',
    original_locale: 'en-GB',
    available_locales: ['en-GB'],
    status: 'published',
    visibility: 'instance',
    effective_visibility: 'instance',
    cover_image_id: null,
    base_servings: 4,
    prep_minutes: null,
    cook_minutes: null,
    rest_minutes: null,
    total_minutes: null,
    difficulty: 'easy',
    tags: [],
    allergens: [],
    diets: [],
    rating_average: null,
    rating_count: 0,
    is_favourite: false,
    has_warning: false,
    unsuitable_for_guests: false,
    season_months: [],
    in_season: false,
    missing_equipment: null,
    kitchen_ready: null,
    variation_count: 0,
    variation_fits_guests: false,
    variation_fits_diets: false,
    can_edit: false,
    owner: { id: 'u1', display_name: 'Anna Huber', avatar_id: null },
    created_via: 'web',
    last_cooked: null,
    created: '2026-11-20T10:00:00Z',
    changed: '2026-11-20T10:00:00Z',
    mirror: null,
    peer_capped: false,
    ...overrides,
  }
}

function mountCard(recipe: RecipeSummary) {
  i18n.global.locale.value = 'enGB'
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } }],
  })
  return mount(RecipeCard, { props: { recipe }, global: { plugins: [router, i18n, OpenVue] } })
}

describe('RecipeCard', () => {
  it('names the owner of a local recipe', () => {
    const wrapper = mountCard(summary())
    expect(wrapper.get('[data-testid="recipe-card-owner"]').text()).toContain('by Anna Huber')
    expect(wrapper.find('[data-testid="recipe-card-source"]').exists()).toBe(false)
  })

  it('names the author and instance of a mirror instead of a local owner', () => {
    const wrapper = mountCard(
      summary({ owner: null, mirror: { instance_name: 'Friends', author_name: 'Mia', author_avatar_id: null } }),
    )
    expect(wrapper.get('[data-testid="recipe-card-source"]').text()).toContain('by Mia · Friends')
    expect(wrapper.find('[data-testid="recipe-card-owner"]').exists()).toBe(false)
  })
})
