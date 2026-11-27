<script setup lang="ts">
import PasswordSection from '@/features/account/components/PasswordSection.vue'
import PasskeysSection from '@/features/account/components/PasskeysSection.vue'
import SessionsSection from '@/features/account/components/SessionsSection.vue'
import TotpSection from '@/features/account/components/TotpSection.vue'
import TrustedDevicesSection from '@/features/account/components/TrustedDevicesSection.vue'
</script>

<template>
  <div class="settings-tab security-tab">
    <PasswordSection />
    <TotpSection />
    <PasskeysSection />
    <SessionsSection />
    <TrustedDevicesSection />
  </div>
</template>

<style scoped lang="scss">
.security-tab {
  gap: var(--space-6);
}
</style>
