import { vi } from 'vitest'

// jsdom does not implement matchMedia; OpenVue's Select and several other
// components call it in their mounted hook. A spec that needs matchMedia to
// behave statefully stubs its own on top of this one.
vi.stubGlobal(
  'matchMedia',
  vi.fn<(query: string) => unknown>().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn<() => void>(),
    removeListener: vi.fn<() => void>(),
    addEventListener: vi.fn<() => void>(),
    removeEventListener: vi.fn<() => void>(),
    dispatchEvent: vi.fn<() => void>(),
  })),
)

// jsdom does not implement ResizeObserver either.
class ResizeObserverMock {
  observe = vi.fn<() => void>()
  unobserve = vi.fn<() => void>()
  disconnect = vi.fn<() => void>()
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)
