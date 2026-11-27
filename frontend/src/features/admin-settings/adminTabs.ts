/**
 * The tabs of the admin area and the sections each one stacks, with the
 * permission every section needs. A tab shows when at least one of its
 * sections does, so someone who may only read the security log sees Auth
 * with just that section.
 */
import { defineAsyncComponent, type Component } from 'vue'

import { Permission } from '@/core/auth/permissions'

export interface AdminSection {
  key: string
  /** Any one of these shows the section. */
  permissions: string[]
  component: Component
  /** Sections that bring their own heading leave this out. */
  titled?: boolean
  /** Props for the component, when one component serves several sections. */
  props?: Record<string, unknown>
  /** A feature switch that has to be on for the section to show. */
  feature?: string
}

export interface AdminTab {
  value: string
  icon: string
  sections: AdminSection[]
  /** A feature switch that has to be on for the tab to show. */
  feature?: string
}

// The loader behind each section's component, so the admin area can fetch
// them all ahead of a tab switch.
const loaders = new WeakMap<Component, () => Promise<unknown>>()

function load(loader: () => Promise<{ default: Component }>): Component {
  const component = defineAsyncComponent(loader)
  loaders.set(component, loader)
  return component
}

export const ADMIN_TABS: AdminTab[] = [
  {
    value: 'host',
    icon: 'mdi-server-network',
    sections: [
      { key: 'host', permissions: [Permission.READ_SETTINGS], component: load(() => import('./components/AdminHostTab.vue')) },
    ],
  },
  {
    value: 'general',
    icon: 'mdi-tune-variant',
    sections: [
      {
        key: 'general',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsGeneralTab.vue')),
        titled: true,
      },
      {
        key: 'features',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminFeaturesSection.vue')),
      },
      {
        key: 'nutrition',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsIntegrationsTab.vue')),
      },
      {
        key: 'privacy',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsPrivacySection.vue')),
      },
      {
        key: 'shopping',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsShoppingSection.vue')),
      },
    ],
  },
  {
    value: 'users',
    icon: 'mdi-account-multiple-outline',
    sections: [
      { key: 'users', permissions: [Permission.WRITE_USERS], component: load(() => import('./components/AdminUsersTab.vue')) },
      {
        key: 'households',
        permissions: [Permission.WRITE_USERS],
        component: load(() => import('./components/AdminHouseholdsSection.vue')),
      },
    ],
  },
  {
    value: 'groups',
    icon: 'mdi-account-group-outline',
    sections: [
      { key: 'groups', permissions: [Permission.WRITE_GROUPS], component: load(() => import('./components/AdminGroupsTab.vue')) },
    ],
  },
  {
    value: 'auth',
    icon: 'mdi-shield-lock-outline',
    sections: [
      {
        key: 'security',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsSecurityTab.vue')),
        titled: true,
      },
      {
        key: 'apiKeys',
        permissions: [Permission.MANAGE_API_KEYS],
        component: load(() => import('./components/SettingsApiKeysTab.vue')),
      },
      {
        key: 'securityLog',
        permissions: [Permission.READ_SECURITY_LOG],
        component: load(() => import('./components/SettingsSecurityLogTab.vue')),
        titled: true,
      },
    ],
  },
  {
    value: 'agents',
    icon: 'mdi-robot-outline',
    sections: [
      {
        key: 'agents',
        permissions: [Permission.READ_SETTINGS, Permission.READ_SECURITY_LOG],
        component: load(() => import('./components/SettingsAgentsTab.vue')),
      },
    ],
  },
  {
    value: 'catalogue',
    icon: 'mdi-clipboard-check-outline',
    sections: [
      {
        key: 'review',
        permissions: [Permission.MANAGE_INGREDIENTS],
        component: load(() => import('./components/AdminCatalogueReviewSection.vue')),
      },
      {
        key: 'referenceUpdates',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminReferenceUpdatesSection.vue')),
      },
      {
        key: 'peerSuggestions',
        permissions: [Permission.READ_SETTINGS],
        feature: 'peering',
        component: load(() => import('./components/AdminPeerSuggestionsSection.vue')),
      },
      {
        key: 'catalogueFile',
        permissions: [Permission.MANAGE_INGREDIENTS, Permission.WRITE_RESOURCES],
        component: load(() => import('./components/AdminCatalogueFileSection.vue')),
      },
      {
        key: 'recipeArchive',
        permissions: [Permission.MANAGE_RECIPES],
        component: load(() => import('./components/AdminRecipeArchiveSection.vue')),
      },
    ],
  },
  {
    value: 'legal',
    icon: 'mdi-scale-balance',
    sections: [
      {
        key: 'privacyStatement',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminLegalSection.vue')),
        props: { kind: 'privacy' },
      },
      {
        key: 'privacyAcknowledgements',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminPrivacyAcknowledgementsSection.vue')),
      },
      {
        key: 'imprint',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminLegalSection.vue')),
        props: { kind: 'imprint' },
      },
    ],
  },
  {
    value: 'storage',
    icon: 'mdi-harddisk',
    sections: [
      { key: 'storage', permissions: [Permission.READ_SETTINGS], component: load(() => import('./components/AdminStorageTab.vue')) },
    ],
  },
  {
    value: 'operations',
    icon: 'mdi-wrench-clock',
    sections: [
      {
        key: 'maintenance',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminMaintenanceSection.vue')),
      },
      {
        key: 'retention',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminRetentionSection.vue')),
      },
      {
        key: 'logs',
        permissions: [Permission.READ_SECURITY_LOG],
        component: load(() => import('./components/AdminLogsSection.vue')),
      },
    ],
  },
  {
    value: 'peers',
    icon: 'mdi-transit-connection-variant',
    feature: 'peering',
    sections: [
      {
        key: 'peers',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminPeersSection.vue')),
      },
      {
        key: 'incomingRecipes',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminIncomingRecipesSection.vue')),
      },
    ],
  },
  {
    value: 'notifications',
    icon: 'mdi-bell-outline',
    sections: [
      {
        key: 'mail',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/SettingsMailTab.vue')),
        titled: true,
      },
      {
        key: 'webhooks',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminWebhooksSection.vue')),
      },
      {
        key: 'banner',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminBannerSection.vue')),
      },
      {
        key: 'notices',
        permissions: [Permission.READ_SETTINGS],
        component: load(() => import('./components/AdminNoticesSection.vue')),
      },
    ],
  },
]

/** Every permission that opens some part of the admin area. */
export const ADMIN_PERMISSIONS: string[] = [
  ...new Set(ADMIN_TABS.flatMap((tab) => tab.sections.flatMap((s) => s.permissions))),
]

/** The tabs and sections a user with `has` may see, leaving out the tabs and sections of switched-off features. */
export function visibleTabs(
  has: (permission: string) => boolean,
  featureOn: (feature: string) => boolean = () => true,
): AdminTab[] {
  return ADMIN_TABS.filter((tab) => !tab.feature || featureOn(tab.feature))
    .map((tab) => ({
      ...tab,
      sections: tab.sections.filter((s) => s.permissions.some(has) && (!s.feature || featureOn(s.feature))),
    }))
    .filter((tab) => tab.sections.length > 0)
}

/**
 * Fetches the code of every section in `tabs` in the background. A section
 * whose code is already there renders its structure at once when its tab
 * opens, instead of popping in once the chunk has arrived.
 */
export function preloadSections(tabs: AdminTab[]): void {
  for (const section of tabs.flatMap((tab) => tab.sections)) {
    // A chunk that fails to load fails again, visibly, when its tab opens.
    loaders.get(section.component)?.().catch(() => undefined)
  }
}
