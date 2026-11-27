<script setup lang="ts">
import { provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import AppBottomNav from '@/app/layouts/AppBottomNav.vue'
import AppHeader from '@/app/layouts/AppHeader.vue'
import AppMaintenanceBanner from '@/app/layouts/AppMaintenanceBanner.vue'
import AppNoticeBanner from '@/app/layouts/AppNoticeBanner.vue'
import AppNoticeDialog from '@/app/layouts/AppNoticeDialog.vue'
import AppSidebar from '@/app/layouts/AppSidebar.vue'
import AppSystemUserWarningDialog from '@/app/layouts/AppSystemUserWarningDialog.vue'
import { useShellScroll } from '@/app/layouts/useShellScroll'
import LegalLinks from '@/shared/components/legal/LegalLinks.vue'
import { useLayoutStore } from '@/core/stores/layoutStore'

const { t } = useI18n()
const route = useRoute()
const layoutStore = useLayoutStore()

// The page scrolls inside <main>, so the shell resets and restores it on
// navigation the way the browser would for the window.
const main = ref<HTMLElement | null>(null)
useShellScroll(main)

// Tells a page that the page bar below exists, so it may teleport a bar there.
provide('pageBar', true)

// On a phone the sidebar is an overlay that More in the bottom nav opens;
// any navigation closes it again.
const moreOpen = ref(false)
watch(
  () => route.fullPath,
  () => {
    moreOpen.value = false
  },
)
</script>

<template>
  <div
    class="app-shell"
    :class="{ 'sidebar-wide': layoutStore.isSidebarWide, 'more-open': moreOpen }"
  >
    <a class="skip-link" href="#main-content">{{ t('common.skipToContent') }}</a>

    <header class="shell-header">
      <AppHeader />
    </header>
    <AppMaintenanceBanner />
    <AppNoticeBanner />
    <AppNoticeDialog />
    <AppSystemUserWarningDialog />

    <div class="shell-body">
      <aside class="shell-sidebar">
        <AppSidebar :overlay="moreOpen" />
      </aside>

      <div class="shell-scrim" aria-hidden="true" @click="moreOpen = false" />

      <main id="main-content" ref="main" class="shell-main" tabindex="-1">
        <!-- A page puts a bar here that spans the whole content area right under the header, such as the admin tabs. -->
        <div id="page-bar" class="page-bar" />
        <div class="page-frame">
          <RouterView />
          <LegalLinks class="page-footer" />
        </div>
      </main>
    </div>

    <footer class="shell-bottom-nav">
      <AppBottomNav v-model:more-open="moreOpen" />
    </footer>
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  --sidebar-w: var(--sidebar-width);

  &.sidebar-wide {
    --sidebar-w: var(--sidebar-width-wide);
  }

  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  // Clipped rather than hidden: a hidden overflow is still a scroll
  // container, so focusing an element positioned outside the scrolling main
  // area (such as a visually hidden file input) scrolled the whole shell,
  // header included, and the user could not scroll it back.
  overflow: clip;
  background: var(--p-content-background);
}

// Visually hidden until it receives keyboard focus, so a keyboard user can
// jump past the header and sidebar into the page content.
.skip-link {
  position: absolute;
  top: -3rem;
  left: 0.5rem;
  z-index: 1000;
  padding: var(--space-2) var(--space-4);
  background: var(--p-primary-500);
  color: var(--on-accent);
  border-radius: var(--p-border-radius-sm);
  transition: top 0.15s ease;

  &:focus-visible {
    top: 0.5rem;
  }
}

.shell-header {
  flex: 0 0 var(--header-height);
  z-index: 10;
}

.shell-body {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
}

// Phone first: the bottom nav carries the navigation, and the sidebar is an
// overlay, always wide, that slides in when More opens it.
.shell-sidebar {
  position: absolute;
  inset: 0 auto 0 0;
  z-index: 20;
  width: var(--sidebar-width-wide);
  transform: translateX(-100%);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
  border-right: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  overflow: hidden auto;
}

// The shadow belongs to the open drawer only; the closed one, just off
// screen, would otherwise cast a strip along the page's left edge.
.more-open .shell-sidebar {
  transform: translateX(0);
  box-shadow: var(--shadow-side);
}

.shell-scrim {
  display: none;
}

.more-open .shell-scrim {
  display: block;
  position: absolute;
  inset: 0;
  z-index: 15;
  background: var(--scrim);
}

.shell-bottom-nav {
  display: block;
  flex: 0 0 calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
  z-index: 10;
}

// The padding is named so a bar teleported into .page-bar can reach past it
// to the edges of the content area with negative margins.
.shell-main {
  --shell-pad-y: var(--space-3);
  --shell-pad-x: var(--space-3);

  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: var(--shell-pad-y) var(--shell-pad-x);
  background: var(--p-surface-50);
  outline: none;
}

// Every page sits in the same frame: full width on a phone, centred and
// capped at --page-width from there on. The frame is at least as tall as
// the scroll area and lays its page out as a flex column, so a page that
// wants to fill the screen (a management table) grows into the rest with
// `flex: 1 1 0; min-height: 0`, while every other page keeps its own height.
.page-frame {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: var(--page-width);
  min-height: 100%;
  margin: 0 auto;
}

// The bar a page teleports in generates no box of its own, so the bar is laid
// out (and sticks) in the scroll area itself rather than in this element.
.page-bar {
  display: contents;
}

// The legal links close every page: below its content, or at the foot of the
// frame when the page is shorter than the screen.
.page-footer {
  margin-top: auto;
  padding-top: var(--space-4);
  color: var(--p-text-muted-color);

  :deep(a) {
    color: inherit;
  }
}

.p-dark .shell-main {
  background: var(--p-surface-950);
}

// From a tablet up the sidebar joins the flow as the narrow rail, which the
// header's toggle widens, and the bottom nav goes.
@media (min-width: $bp-sm) {
  .shell-sidebar {
    position: static;
    z-index: auto;
    flex: 0 0 var(--sidebar-w);
    width: var(--sidebar-w);
    transform: none;
    transition:
      flex-basis 0.2s ease,
      width 0.2s ease;
    box-shadow: none;
  }

  .shell-scrim,
  .more-open .shell-scrim,
  .shell-bottom-nav {
    display: none;
  }

  .shell-main {
    --shell-pad-y: var(--space-4);
    --shell-pad-x: var(--space-4);
  }
}

@media (min-width: $bp-md) {
  .shell-main {
    --shell-pad-y: var(--space-5);
    --shell-pad-x: var(--space-6);
  }
}

// On paper only the page itself is printed: the header, the navigation, the
// banners and the legal links stay on screen, and the shell stops clipping
// its content to the window so a long page runs over several sheets.
@media print {
  .app-shell {
    position: static;
    display: block;
    overflow: visible;
    background: none;
  }

  .skip-link,
  .shell-header,
  .shell-sidebar,
  .shell-scrim,
  .shell-bottom-nav,
  .page-footer,
  .page-bar,
  .maintenance-banner,
  .notice-banner {
    display: none;
  }

  .shell-body {
    display: block;
  }

  .shell-main,
  .p-dark .shell-main {
    overflow: visible;
    padding: 0;
    background: none;
  }

  .page-frame {
    max-width: none;
    min-height: 0;
  }
}
</style>
