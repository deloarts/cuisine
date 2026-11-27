<script setup lang="ts">
import { ref, watch } from 'vue'
import QRCode from 'qrcode'

const props = defineProps<{ uri: string; label: string }>()

const dataUrl = ref<string | null>(null)

// The QR code is drawn in the browser, so the secret never leaves it again.
watch(
  () => props.uri,
  async (uri) => {
    dataUrl.value = uri ? await QRCode.toDataURL(uri, { margin: 1, width: 200 }) : null
  },
  { immediate: true },
)
</script>

<template>
  <img v-if="dataUrl" :src="dataUrl" :alt="label" class="totp-qr" width="200" height="200" />
</template>

<style scoped lang="scss">
// A QR code needs a light quiet zone to scan, in either theme.
.totp-qr {
  display: block;
  margin: 0 auto;
  background: var(--paper);
  border-radius: var(--p-border-radius-md);
}
</style>
