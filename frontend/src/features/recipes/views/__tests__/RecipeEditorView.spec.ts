import { flushPromises, mount } from '@vue/test-utils'
import { AxiosError, type AxiosResponse } from 'axios'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { webApi } from '@/core/api/webRequest'
import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { CurrentUserResponse } from '@/core/types/user'
import { editorDrafts } from '@/core/utils/editorDrafts'
import type {
  RecipeDetailResponse,
  RecipeEditResponse,
  VariationResponse,
  updateRecipe as UpdateRecipe,
} from '@/features/recipes/api/recipes'
import RecipeEditorView from '@/features/recipes/views/RecipeEditorView.vue'
import VariationEditorView from '@/features/recipes/views/VariationEditorView.vue'
import PageHeader from '@/shared/components/PageHeader.vue'

type RecipeResponse = Awaited<ReturnType<typeof UpdateRecipe>>

const getRecipeForEdit = vi.fn<(id: string) => Promise<RecipeEditResponse>>()
const createRecipe = vi.fn<(body: unknown) => Promise<RecipeResponse>>()
const updateRecipe = vi.fn<(id: string, body: unknown) => Promise<RecipeResponse>>()
const publishRecipe = vi.fn<(id: string) => Promise<void>>()
const getRecipe = vi.fn<(id: string) => Promise<RecipeDetailResponse>>()
const createVariation = vi.fn<(id: string, body: unknown) => Promise<VariationResponse>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  getRecipeForEdit: (id: string) => getRecipeForEdit(id),
  createRecipe: (body: unknown) => createRecipe(body),
  updateRecipe: (id: string, body: unknown) => updateRecipe(id, body),
  publishRecipe: (id: string) => publishRecipe(id),
  getRecipe: (id: string) => getRecipe(id),
  createVariation: (id: string, body: unknown) => createVariation(id, body),
  getVariation: vi.fn<() => void>(),
  updateVariation: vi.fn<() => void>(),
  getPrivacySettings: () =>
    Promise.resolve({
      default_recipe_visibility: 'instance',
      users_may_change_visibility: true,
      allow_public_recipes: false,
      index_public_recipes: false,
    }),
  listShareTargets: () => Promise.resolve([]),
  listEquipment: () => Promise.resolve([]),
  listGroups: () => Promise.resolve([]),
  searchIngredients: () => Promise.resolve([]),
  searchRecipes: () => Promise.resolve([]),
  uploadImage: vi.fn<() => void>(),
}))

// The catalogue lists come from the shared resources, not from the feature's api module.
vi.mock('@/shared/cookbook/useCookbookResources', () => ({
  useCookbookResources: () => ({
    units: ref([]),
    tags: ref([]),
    categories: ref([]),
    families: ref([]),
    load: () => Promise.resolve(),
    reload: () => Promise.resolve(),
  }),
}))

// The confirm dialog itself lives in the app shell; the spec answers it.
const confirmAnswer = vi.fn<() => boolean>(() => true)
vi.mock('openvue/useconfirm', () => ({
  useConfirm: () => ({
    require: (options: { accept?: () => void; reject?: () => void }) =>
      confirmAnswer() ? options.accept?.() : options.reject?.(),
  }),
}))

const originalMatchMedia = window.matchMedia

// The header shows separate buttons from the small breakpoint up and one
// split button below it.
function setWideScreen(wide: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn<(query: string) => unknown>().mockImplementation((query: string) => ({
      matches: wide && query.includes('min-width'),
      media: query,
      onchange: null,
      addListener: vi.fn<() => void>(),
      removeListener: vi.fn<() => void>(),
      addEventListener: vi.fn<() => void>(),
      removeEventListener: vi.fn<() => void>(),
      dispatchEvent: vi.fn<() => void>(),
    })),
  )
}

function editResponse(status: 'draft' | 'published'): RecipeEditResponse {
  return {
    ...({} as RecipeEditResponse),
    id: 'r1',
    status,
    can_edit: true,
    can_change_visibility: true,
    effective_visibility: 'instance',
    peer_capped: false,
    shared_peers: [],
    peer_hidden_sub_recipe_ids: [],
    original_locale: 'en-GB',
    translations: { 'en-GB': { title: 'Goulash', description: '', tips: '' } },
    base_servings: 4,
    prep_minutes: null,
    cook_minutes: null,
    rest_minutes: null,
    difficulty: 'easy',
    cover_image_id: null,
    source_url: null,
    source_name: null,
    tag_ids: [],
    yield_amount: null,
    yield_unit_id: null,
    visibility: 'instance',
    shared_user_ids: [],
    shared_group_ids: [],
    steps: [
      {
        id: 's1',
        translations: { 'en-GB': { text: 'Brown the onions.' } },
        duration_minutes: null,
        image_id: null,
        ingredients: [],
        equipment: [],
      },
    ],
  }
}

function savedResponse(status: 'draft' | 'published'): RecipeResponse {
  return {
    ...({} as RecipeResponse),
    id: 'r1',
    status,
    effective_visibility: 'instance',
    less_visible_sub_recipe_ids: [],
  }
}

// Every mounted editor is unmounted after its test, so no pending draft
// write lands in the next one.
const mounted: { unmount: () => void }[] = []
afterEach(() => {
  for (const wrapper of mounted.splice(0)) {
    try {
      wrapper.unmount()
    } catch {
      // Already unmounted by the test itself.
    }
  }
})

async function mountAt(path: string, component: typeof RecipeEditorView | typeof VariationEditorView) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/recipes', name: 'recipes', component: { template: '<div />' } },
      { path: '/recipes/new', name: 'recipe-new', component },
      { path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } },
      { path: '/recipes/:id/edit', name: 'recipe-edit', component },
      { path: '/recipes/:id/variations/new', name: 'recipe-variation-new', component },
    ],
  })
  await router.push(path)
  const wrapper = mount(component, {
    attachTo: document.body,
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
  })
  mounted.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}

// The split button's menu is teleported to the body; its entries are found there by text.
async function pickFromMenu(wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper'], label: string) {
  await wrapper.get('[data-testid="editor-actions-more"]').trigger('click')
  await flushPromises()
  const items = [...document.body.querySelectorAll('[role="menuitem"]')]
  const item = items.find((el) => el.textContent?.trim() === label)
  expect(item, `menu entry "${label}"`).toBeDefined()
  ;(item!.firstElementChild as HTMLElement).click()
  await flushPromises()
}

const header = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) => wrapper.getComponent(PageHeader)

describe('RecipeEditorView header actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipeForEdit.mockReset()
    createRecipe.mockReset()
    updateRecipe.mockReset()
    publishRecipe.mockReset().mockResolvedValue()
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  it('puts cancel, save draft and publish as buttons in the header on a wide screen', async () => {
    setWideScreen(true)
    const { wrapper } = await mountAt('/recipes/new', RecipeEditorView)
    const labels = header(wrapper)
      .findAll('[data-testid^="editor-action-"]')
      .map((b) => b.text())
    expect(labels).toEqual(['Cancel', 'Save draft', 'Save and publish'])
    expect(wrapper.find('[data-testid="editor-actions-more"]').exists()).toBe(false)
  })

  it('validates instead of saving when publish is pressed on an empty form', async () => {
    setWideScreen(true)
    const { wrapper } = await mountAt('/recipes/new', RecipeEditorView)
    await wrapper.get('[data-testid="editor-action-publish"]').trigger('click')
    await flushPromises()
    expect(createRecipe).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('The recipe needs a title.')
  })

  it('collapses into a split button with publish as the main action on a phone', async () => {
    setWideScreen(false)
    const { wrapper, router } = await mountAt('/recipes/new', RecipeEditorView)
    expect(header(wrapper).get('[data-testid="editor-action-publish"]').text()).toBe('Save and publish')
    expect(wrapper.find('[data-testid="editor-action-save"]').exists()).toBe(false)

    await pickFromMenu(wrapper, 'Cancel')
    expect(router.currentRoute.value.name).toBe('recipes')
  })

  it('saves a draft without publishing it from the split button menu', async () => {
    setWideScreen(false)
    getRecipeForEdit.mockResolvedValue(editResponse('draft'))
    updateRecipe.mockResolvedValue(savedResponse('draft'))
    const { wrapper, router } = await mountAt('/recipes/r1/edit', RecipeEditorView)

    await pickFromMenu(wrapper, 'Save draft')
    expect(updateRecipe).toHaveBeenCalledOnce()
    expect(publishRecipe).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('recipe')
  })

  it('publishes a draft from the main button', async () => {
    setWideScreen(false)
    getRecipeForEdit.mockResolvedValue(editResponse('draft'))
    updateRecipe.mockResolvedValue(savedResponse('draft'))
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)

    await wrapper.get('[data-testid="editor-action-publish"]').trigger('click')
    await flushPromises()
    expect(updateRecipe).toHaveBeenCalledOnce()
    expect(publishRecipe).toHaveBeenCalledWith('r1')
  })

  it('offers only save and cancel for a published recipe', async () => {
    setWideScreen(true)
    getRecipeForEdit.mockResolvedValue(editResponse('published'))
    updateRecipe.mockResolvedValue(savedResponse('published'))
    const { wrapper, router } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    const labels = header(wrapper)
      .findAll('[data-testid^="editor-action-"]')
      .map((b) => b.text())
    expect(labels).toEqual(['Cancel', 'Save'])

    await wrapper.get('[data-testid="editor-action-save"]').trigger('click')
    await flushPromises()
    expect(updateRecipe).toHaveBeenCalledOnce()
    expect(publishRecipe).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('recipe')
  })

  it('shows no actions when the recipe may not be edited', async () => {
    setWideScreen(true)
    getRecipeForEdit.mockResolvedValue({ ...editResponse('draft'), can_edit: false })
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    expect(header(wrapper).find('[data-testid^="editor-action-"]').exists()).toBe(false)
  })
})

describe('VariationEditorView header actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockReset().mockResolvedValue({
      ...({} as RecipeDetailResponse),
      id: 'r1',
      title: 'Goulash',
      steps: [],
    })
    createVariation.mockReset()
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  it('puts cancel and save in the header on a wide screen', async () => {
    setWideScreen(true)
    const { wrapper } = await mountAt('/recipes/r1/variations/new', VariationEditorView)
    const labels = header(wrapper)
      .findAll('[data-testid^="editor-action-"]')
      .map((b) => b.text())
    expect(labels).toEqual(['Cancel', 'Save the variation'])
  })

  it('validates from the split button on a phone and cancels from its menu', async () => {
    setWideScreen(false)
    const { wrapper, router } = await mountAt('/recipes/r1/variations/new', VariationEditorView)

    await wrapper.get('[data-testid="editor-action-save"]').trigger('click')
    await flushPromises()
    expect(createVariation).not.toHaveBeenCalled()

    await pickFromMenu(wrapper, 'Cancel')
    expect(router.currentRoute.value.name).toBe('recipe')
  })
})

function signIn(id: string) {
  useCurrentUserStore().user = { ...({} as CurrentUserResponse), id, effective_permissions: [] }
}

describe('recipe editor drafts on the device', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    localStorage.clear()
    setWideScreen(true)
    signIn('u1')
    getRecipeForEdit.mockReset().mockResolvedValue(editResponse('published'))
    updateRecipe.mockReset().mockResolvedValue(savedResponse('published'))
    confirmAnswer.mockReset().mockReturnValue(true)
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  async function editTitle(path: string, title: string) {
    const { wrapper } = await mountAt(path, RecipeEditorView)
    await wrapper.get('#editor-title').setValue(title)
    // Leaving the editor writes the pending change at once.
    wrapper.unmount()
  }

  it('brings unsaved changes back after leaving and coming back', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    expect(editorDrafts.read('u1', 'recipe:r1')).not.toBeNull()

    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash with dumplings')
    expect(wrapper.get('[data-testid="draft-notice"]').text()).toContain('Your unsaved changes from')
    expect(wrapper.get('[data-testid="draft-notice"]').text()).not.toContain('saved version was changed')
  })

  it('removes images of a restored draft that the server no longer has', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    const stored = editorDrafts.read<{ cover_image_id: string | null }>('u1', 'recipe:r1')!
    editorDrafts.write('u1', 'recipe:r1', stored.base, { ...stored.data, cover_image_id: 'gone-image' })
    const get = vi.spyOn(webApi, 'get').mockRejectedValue(
      new AxiosError('Not found', 'ERR_BAD_REQUEST', undefined, undefined, { status: 404 } as AxiosResponse),
    )

    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await flushPromises()
    expect(get).toHaveBeenCalledWith('/files/{file_id}', { path: { file_id: 'gone-image' } })
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash with dumplings')
    expect(wrapper.get('[data-testid="draft-notice"]').text()).toContain('One image was no longer available')
    wrapper.unmount()
    expect(editorDrafts.read<{ cover_image_id: string | null }>('u1', 'recipe:r1')!.data.cover_image_id).toBeNull()
    get.mockRestore()
  })

  it('keeps the images of a restored draft when the check fails for another reason', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    const stored = editorDrafts.read<{ cover_image_id: string | null }>('u1', 'recipe:r1')!
    editorDrafts.write('u1', 'recipe:r1', stored.base, { ...stored.data, cover_image_id: 'maybe-image' })
    const get = vi.spyOn(webApi, 'get').mockRejectedValue(new Error('offline'))

    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await flushPromises()
    expect(wrapper.get('[data-testid="draft-notice"]').text()).not.toContain('no longer available')
    wrapper.unmount()
    expect(editorDrafts.read<{ cover_image_id: string | null }>('u1', 'recipe:r1')!.data.cover_image_id).toBe('maybe-image')
    get.mockRestore()
  })

  it('keeps a new recipe draft under its own key', async () => {
    await editTitle('/recipes/new', 'Strudel')
    expect(editorDrafts.read('u1', 'recipe:new')).not.toBeNull()
    expect(editorDrafts.read('u1', 'recipe:r1')).toBeNull()
  })

  it('says so when the recipe changed on the server after the draft was stored', async () => {
    getRecipeForEdit.mockResolvedValue({ ...editResponse('published'), changed: '2026-11-01T10:00:00Z' })
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    getRecipeForEdit.mockResolvedValue({ ...editResponse('published'), changed: '2026-11-02T10:00:00Z' })

    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash with dumplings')
    expect(wrapper.get('[data-testid="draft-notice"]').text()).toContain('saved version was changed')
  })

  it('drops the draft after a successful save', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    const { wrapper, router } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await wrapper.get('[data-testid="editor-action-save"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(editorDrafts.read('u1', 'recipe:r1')).toBeNull()
  })

  it('puts the saved version back when the draft is discarded', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await wrapper.get('[data-testid="draft-discard"]').trigger('click')
    await flushPromises()
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash')
    expect(wrapper.find('[data-testid="draft-notice"]').exists()).toBe(false)
    expect(editorDrafts.read('u1', 'recipe:r1')).toBeNull()
  })

  it('never shows a draft of another recipe or another user', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')

    getRecipeForEdit.mockResolvedValue({ ...editResponse('published'), id: 'r2' })
    const other = await mountAt('/recipes/r2/edit', RecipeEditorView)
    expect((other.wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash')
    other.wrapper.unmount()

    signIn('u2')
    getRecipeForEdit.mockResolvedValue(editResponse('published'))
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash')
    expect(wrapper.find('[data-testid="draft-notice"]').exists()).toBe(false)
    expect(editorDrafts.read('u1', 'recipe:r1')).not.toBeNull()
  })

  it('asks before cancelling unsaved changes and keeps them when the user stays', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await wrapper.get('#editor-title').setValue('Goulash with dumplings')

    confirmAnswer.mockReturnValue(false)
    await wrapper.get('[data-testid="editor-action-cancel"]').trigger('click')
    await flushPromises()
    expect(confirmAnswer).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.name).toBe('recipe-edit')

    confirmAnswer.mockReturnValue(true)
    await wrapper.get('[data-testid="editor-action-cancel"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(editorDrafts.read('u1', 'recipe:r1')).toBeNull()
  })

  it('cancels without asking when nothing changed', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await wrapper.get('[data-testid="editor-action-cancel"]').trigger('click')
    await flushPromises()
    expect(confirmAnswer).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('recipe')
  })

  it('removes the drafts of a user who signs out', async () => {
    await editTitle('/recipes/r1/edit', 'Goulash with dumplings')
    editorDrafts.write('u2', 'recipe:r1', null, { other: true })
    useCurrentUserStore().clear()
    expect(editorDrafts.read('u1', 'recipe:r1')).toBeNull()
    expect(editorDrafts.read('u2', 'recipe:r1')).not.toBeNull()
  })
})

describe('variation editor drafts on the device', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    localStorage.clear()
    setWideScreen(true)
    signIn('u1')
    getRecipe.mockReset().mockResolvedValue({
      ...({} as RecipeDetailResponse),
      id: 'r1',
      title: 'Goulash',
      locale: 'en-GB',
      changed: '2026-11-01T10:00:00Z',
      steps: [],
    })
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  it('brings a new variation back under the recipe it belongs to', async () => {
    const first = await mountAt('/recipes/r1/variations/new', VariationEditorView)
    await first.wrapper.get('#variation-name').setValue('With dumplings')
    first.wrapper.unmount()
    expect(editorDrafts.read('u1', 'variation:r1:new')).not.toBeNull()

    const { wrapper } = await mountAt('/recipes/r1/variations/new', VariationEditorView)
    expect((wrapper.get('#variation-name').element as HTMLInputElement).value).toBe('With dumplings')
    expect(wrapper.find('[data-testid="draft-notice"]').exists()).toBe(true)
  })
})

describe('recipe editor steps tab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    setWideScreen(true)
    getRecipeForEdit.mockReset().mockResolvedValue(editResponse('published'))
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  it('shows the step pickers without section titles, still named for assistive technology', async () => {
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    const stepsTab = wrapper.findAll('[role="tab"]').find((tab) => tab.text().startsWith('Steps'))
    await stepsTab!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).not.toContain('Ingredients of this step')
    expect(wrapper.text()).not.toContain('Equipment for this step')
    const labels = wrapper.findAll('label').map((label) => label.text())
    expect(labels).toContain('Add an ingredient')
    expect(labels).toContain('Add equipment…')
  })
})

describe('recipe editor declared ingredient list', () => {
  const withLines = (): RecipeEditResponse => ({
    ...editResponse('published'),
    steps: [
      {
        ...editResponse('published').steps[0]!,
        ingredients: [
          {
            id: 'l1',
            ingredient_id: 'onion',
            sub_recipe_id: null,
            ingredient_name: 'Onion',
            amount: 2,
            unit_id: null,
            notes: {},
          },
        ],
      },
    ],
    ingredients: [
      {
        id: 'd1',
        ingredient_id: 'paprika',
        sub_recipe_id: null,
        ingredient_name: 'Paprika',
        amount: null,
        unit_id: null,
        notes: { 'en-GB': { note: 'sweet' } },
      },
    ],
  })

  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    localStorage.clear()
    setWideScreen(true)
    signIn('u1')
    getRecipeForEdit.mockReset().mockResolvedValue(withLines())
    updateRecipe.mockReset().mockResolvedValue(savedResponse('published'))
    confirmAnswer.mockReset().mockReturnValue(true)
  })

  afterEach(() => {
    vi.stubGlobal('matchMedia', originalMatchMedia)
    document.body.innerHTML = ''
  })

  async function openSteps(wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) {
    const stepsTab = wrapper.findAll('[role="tab"]').find((tab) => tab.text().startsWith('Steps'))
    await stepsTab!.trigger('click')
    await flushPromises()
  }

  it('shows the summary above the first step and sends the declared lines with their ids', async () => {
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await openSteps(wrapper)
    const summary = wrapper.get('[data-testid="ingredient-summary"]')
    expect(summary.text()).toContain('Paprika')
    expect(summary.get('[data-testid="summary-step-only"]').text()).toContain('Onion')

    await summary.get('[data-testid="summary-add-step-only"]').trigger('click')
    await wrapper.get('[data-testid="editor-action-save"]').trigger('click')
    await flushPromises()
    const body = updateRecipe.mock.calls[0]![1] as { ingredients: unknown[] }
    expect(body.ingredients).toEqual([
      { id: 'd1', ingredient_id: 'paprika', amount: null, unit_id: null, notes: { 'en-GB': { note: 'sweet' } } },
      { ingredient_id: 'onion', amount: 2, unit_id: null, notes: {} },
    ])
  })

  it('keeps the declared lines in the draft on the device', async () => {
    const first = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await openSteps(first.wrapper)
    await first.wrapper.get('[data-testid="summary-add-step-only"]').trigger('click')
    first.wrapper.unmount()
    const stored = editorDrafts.read<{ ingredients: { ingredient_id: string }[] }>('u1', 'recipe:r1')
    expect(stored?.data.ingredients.map((l) => l.ingredient_id)).toEqual(['paprika', 'onion'])

    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await openSteps(wrapper)
    expect(wrapper.find('[data-testid="draft-notice"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="summary-line"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="summary-step-only"]').exists()).toBe(false)
  })

  it('reads a draft stored before the declared list existed as one without lines', async () => {
    getRecipeForEdit.mockResolvedValue({ ...withLines(), ingredients: [] })
    const first = await mountAt('/recipes/r1/edit', RecipeEditorView)
    await first.wrapper.get('#editor-title').setValue('Goulash with dumplings')
    first.wrapper.unmount()
    const stored = editorDrafts.read<Record<string, unknown>>('u1', 'recipe:r1')!
    delete stored.data.ingredients
    editorDrafts.write('u1', 'recipe:r1', stored.base, stored.data)

    getRecipeForEdit.mockResolvedValue(withLines())
    const { wrapper } = await mountAt('/recipes/r1/edit', RecipeEditorView)
    expect((wrapper.get('#editor-title').element as HTMLInputElement).value).toBe('Goulash with dumplings')
    await openSteps(wrapper)
    expect(wrapper.findAll('[data-testid="summary-line"]')).toHaveLength(0)
  })
})
