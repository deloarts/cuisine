<script setup lang="ts">
/**
 * The QR code at the foot of a printed recipe. It encodes the absolute link
 * through the resolver route (`/r/<public id>`), so a phone that scans the
 * paper opens the recipe in this cookbook, after signing in if needed. The
 * code is drawn in the browser; no external service sees the link. The block
 * shows only on paper.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import QRCode from 'qrcode'

const props = defineProps<{ publicId: string }>()

const { t } = useI18n()

const url = computed(() => `${window.location.origin}/r/${encodeURIComponent(props.publicId)}`)
const dataUrl = ref<string | null>(null)

watch(
  url,
  async (value) => {
    try {
      dataUrl.value = await QRCode.toDataURL(value, { margin: 1, width: 240 })
    } catch {
      // Paper without a code still carries the recipe.
      dataUrl.value = null
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="print-qr" data-testid="recipe-print-qr">
    <img v-if="dataUrl" :src="dataUrl" :alt="t('recipes.print.qrAlt')" class="print-qr-image" />
    <p class="print-qr-text">
      {{ t('recipes.print.qrCaption') }}
      <span class="print-qr-url">{{ url }}</span>
    </p>
  </div>
</template>

<style scoped lang="scss">
.print-qr {
  display: none;
}

@media print {
  .print-qr {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    break-inside: avoid;
  }

  .print-qr-image {
    width: 2.5cm;
    height: 2.5cm;
  }

  .print-qr-text {
    display: flex;
    flex-direction: column;
    font-size: var(--font-size-sm);
  }

  .print-qr-url {
    overflow-wrap: anywhere;
    font-size: var(--font-size-xs);
  }
}
</style>
