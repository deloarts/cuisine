import { createApp, watch } from 'vue'
import { createPinia } from 'pinia'

import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import ConfirmationService from 'openvue/confirmationservice'
import Tooltip from 'openvue/tooltip'

import { i18n } from '@/core/i18n'
import { applyOpenVueLocale } from '@/core/i18n/openvueLocale'
import { defaultThemePreset } from '@/core/config/themePresets'

import App from '@/App.vue'
import router from '@/router'

import '@fontsource-variable/nunito'
import '@fontsource/lobster'
import '@mdi/font/css/materialdesignicons.css'
import '@/assets/styles/main.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(OpenVue, {
  theme: {
    preset: defaultThemePreset,
    options: { darkModeSelector: '.p-dark' },
  },
  ripple: true,
  locale: {
    dateFormat: 'yy-mm-dd',
    firstDayOfWeek: 1,
  },
})
// OpenVue's own texts follow the UI language.
watch(
  i18n.global.locale,
  (locale) => applyOpenVueLocale(app.config.globalProperties.$primevue.config, locale),
  { immediate: true },
)
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

app.mount('#app')
