import { updatePrimaryPalette, updateSurfacePalette, usePreset } from '@openvue/themes'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { PRIMARY_COLORS, SURFACES } from '@/core/config/colorPalettes'
import { themePresets } from '@/core/config/themePresets'
import { safeStorage } from '@/core/utils/safeStorage'

export const DEFAULT_PRIMARY = 'cuisine'
export const DEFAULT_SURFACE = 'neutral'

/** The OS preference, the theme everybody gets until they sign in. */
export function prefersDarkMode(): boolean {
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false
}

const SIDEBAR_WIDE_STORAGE_KEY = 'sidebarWide'

export const useLayoutStore = defineStore('layout', () => {
  const darkMode = ref(prefersDarkMode())
  const primary = ref(DEFAULT_PRIMARY)
  const surface = ref(DEFAULT_SURFACE)
  const sidebarWide = ref(safeStorage.get(SIDEBAR_WIDE_STORAGE_KEY) === 'true')

  // Set once the user's saved theme is applied, so the boot default can
  // never overwrite it, whichever finishes first on startup.
  let hasUserTheme = false

  function setDarkMode(value: boolean) {
    darkMode.value = value
    document.documentElement.classList.toggle('p-dark', value)
  }

  // Paper is always light: the dark theme steps aside while the browser
  // prints, so OpenVue's variables give dark ink on white, and comes back
  // afterwards.
  window.addEventListener('beforeprint', () => {
    document.documentElement.classList.remove('p-dark')
  })
  window.addEventListener('afterprint', () => {
    document.documentElement.classList.toggle('p-dark', darkMode.value)
  })

  function updateColors(type: 'primary' | 'surface', colorName: string) {
    if (type === 'primary') {
      const color = PRIMARY_COLORS.find((c) => c.name === colorName)
      if (!color) return
      primary.value = colorName
      updatePrimaryPalette(color.palette)
    } else {
      const color = SURFACES.find((s) => s.name === colorName)
      if (!color) return
      surface.value = colorName
      updateSurfacePalette(color.palette)
    }
  }

  /**
   * Boot-time theme: the OS dark-mode preference and the default palettes.
   * A no-op once a signed-in user's own theme has been applied.
   */
  function initDefaultTheme() {
    if (hasUserTheme) return
    updateColors('primary', DEFAULT_PRIMARY)
    updateColors('surface', DEFAULT_SURFACE)
    setDarkMode(prefersDarkMode())
  }

  /**
   * Applies the user's saved theme. usePreset() replaces the whole theme,
   * palettes included, so the colours are painted again after it.
   */
  function applyUserTheme(preset: string, primaryName: string, surfaceName: string, dark: boolean) {
    hasUserTheme = true
    const resolved = themePresets[preset]
    if (resolved) usePreset(resolved)
    updateColors('primary', primaryName)
    updateColors('surface', surfaceName)
    setDarkMode(dark)
  }

  function toggleSidebarWide() {
    sidebarWide.value = !sidebarWide.value
    safeStorage.set(SIDEBAR_WIDE_STORAGE_KEY, String(sidebarWide.value))
  }

  return {
    isDarkMode: computed(() => darkMode.value),
    primary: computed(() => primary.value),
    surface: computed(() => surface.value),
    isSidebarWide: computed(() => sidebarWide.value),
    initDefaultTheme,
    applyUserTheme,
    updateColors,
    setDarkMode,
    toggleSidebarWide,
  }
})
