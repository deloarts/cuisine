<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import SteamBackdrop from '@/app/layouts/SteamBackdrop.vue'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

const publicInfo = usePublicInfoStore()

// The photo an administrator set in the General tab. Its key is part of the URL,
// so a new photo is fetched at once instead of waiting out the cached old one.
const backgroundUrl = computed(() => {
  const key = publicInfo.info?.login_background_key
  return key ? `${import.meta.env.VITE_API_URL ?? ''}/api/v1/public/branding/login-background?v=${key}` : null
})
// The steam is on unless the administrator turned it off; until the public
// info has arrived it waits, so it never flashes up on an instance without it.
const showSteam = computed(() => publicInfo.info?.login_steam === true)
const loaded = ref(false)
watch(backgroundUrl, () => {
  loaded.value = false
})
</script>

<template>
  <div class="auth-layout">
    <div v-if="!backgroundUrl" class="auth-glow" />
    <div v-else class="auth-photo" :class="{ loaded }">
      <img :src="backgroundUrl" alt="" @load="loaded = true" />
    </div>
    <SteamBackdrop v-if="showSteam" />
    <RouterView />
  </div>
</template>

<style scoped lang="scss">
// The sign-in screens are dark in every theme, so they carry their own
// palette. The views and steps rendered inside the layout inherit it.
.auth-layout {
  --auth-backdrop: #0c0806;
  --auth-glow-a: rgb(194 65 12 / 35%);
  --auth-glow-b: rgb(251 146 60 / 12%);
  --auth-glow: radial-gradient(circle at 30% 70%, var(--auth-glow-a), transparent 45%);
  --auth-glow-far: radial-gradient(circle at 70% 30%, var(--auth-glow-b), transparent 40%);
  --auth-photo-shade:
    radial-gradient(ellipse at center, rgb(12 8 6 / 45%), rgb(12 8 6 / 25%) 60%, rgb(12 8 6 / 70%));
  --auth-card: rgb(14 10 8 / 88%);
  --auth-ink: #fff;
  --auth-text-strong: rgb(255 255 255 / 90%);
  --auth-text: rgb(255 255 255 / 65%);
  --auth-text-muted: rgb(255 255 255 / 48%);
  --auth-text-faint: rgb(255 255 255 / 35%);
  --auth-field: rgb(255 255 255 / 4%);
  --auth-field-hover: rgb(255 255 255 / 6%);
  --auth-line: rgb(255 255 255 / 8%);
  --auth-sheen: rgb(255 255 255 / 13%);
  --auth-accent: #c2410c;
  --auth-accent-hover: #dc5a1e;
  --auth-accent-active: #9a3412;
  --auth-accent-text: rgb(251 146 60 / 90%);
  --auth-focus-fill: rgb(194 65 12 / 8%);
  --auth-hover-border: rgb(234 88 12 / 30%);
  --auth-focus-border: rgb(251 146 60 / 70%);
  --auth-focus-glow: 0 0 0 3px rgb(194 65 12 / 14%), 0 0 18px rgb(194 65 12 / 18%);
  --auth-card-shadow:
    0 0 0 1px rgb(194 65 12 / 14%), inset 0 1px 0 rgb(255 255 255 / 6%), 0 12px 80px rgb(0 0 0 / 80%),
    0 0 100px rgb(194 65 12 / 10%);
  --auth-submit-shadow: 0 2px 18px rgb(194 65 12 / 30%);
  --auth-submit-shadow-hover: 0 4px 28px rgb(234 88 12 / 45%);

  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--auth-backdrop);
  overflow: auto;
}

// A slow, warm glow behind the card, like embers under a pan. Its two warm
// spots drift on their own rhythms, slowly growing, shrinking and moving
// closer together and apart; the movement is kept faint on purpose.
.auth-glow {
  position: absolute;
  inset: -20%;
  background: var(--auth-glow);
  animation: drift 26s ease-in-out infinite alternate;
  pointer-events: none;

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--auth-glow-far);
    animation: drift-far 37s ease-in-out -11s infinite alternate;
  }
}

// The background photo starts black and fades in only once it has loaded, so a
// slow connection never shows it arriving line by line. The shade keeps the
// card readable over a bright picture.
.auth-photo {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 1.8s ease-out;
  pointer-events: none;

  &.loaded {
    opacity: 1;
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--auth-photo-shade);
  }
}

@keyframes drift {
  from {
    transform: translate3d(-3%, 2%, 0) scale(1);
  }

  to {
    transform: translate3d(3%, -2%, 0) scale(1.08);
  }
}

// Moves against the near spot, so the two drift apart and back together.
@keyframes drift-far {
  from {
    transform: translate3d(-3%, 2%, 0) scale(0.95);
  }

  to {
    transform: translate3d(3%, -3%, 0) scale(1.06);
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-glow,
  .auth-glow::after {
    animation: none;
  }

  .auth-photo {
    transition: none;
  }
}
</style>
