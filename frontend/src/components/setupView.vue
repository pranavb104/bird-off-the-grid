<template>
  <div class="dither-card dither-border bg-[var(--color-card)] rounded-lg shadow-lg p-6 max-w-md w-full">
    <div class="dither-header rounded mb-2 px-1">
      <h2 class="text-3xl font-bold text-[var(--color-primary)]">BirdNet OffGrid</h2>
    </div>
    <p class="text-lg text-[var(--color-text-secondary)] mb-4">Your Device is {{ socketStatus }}</p>
    <div class="text-lg font-semibold text-[var(--color-text-secondary)] bg-[var(--color-input-bg)] px-5 py-2.5 rounded-lg border border-[var(--color-border)] mb-6">
      {{ localTime }}
    </div>

    <button v-if="!setupComplete && socketStatus === 'Connected'" @click="goToScriptPage"
      class="dither-btn bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white text-xl py-3 px-6 rounded-lg transition-colors">
      Setup ->
    </button>

    <div v-if="setupComplete && socketStatus === 'Connected'" class="flex items-center justify-between gap-3">
      <button @click="$router.push('/dashboard')"
        class="dither-btn bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white text-xl py-3 px-6 rounded-lg transition-colors cursor-pointer">
        Start ->
      </button>
      <button @click="resetData" :disabled="isResetting"
        class="dither-btn bg-[var(--color-card-alt)] hover:bg-[var(--color-border)] text-[var(--color-text-secondary)] text-xl py-3 px-6 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
        Reset
      </button>
    </div>

    <p v-if="resetMessage" class="text-[var(--color-success)] text-sm mt-3">{{ resetMessage }}</p>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: "setupView",
  props: {
    localTime: {
      type: String,
      required: true
    },
    socketStatus: {
      type: String,
      required: true
    }
  },

  data() {
    return {
      setupComplete: false,
      isResetting: false,
      resetMessage: '',
    };
  },

  created() {
    this.checkSetupComplete();
  },

  methods: {
    async checkSetupComplete() {
      try {
        const resp = await api.get('/setup-complete');
        this.setupComplete = resp.data.complete;
      } catch {
        // Pi not reachable yet — stay on setup screen
      }
    },
    goToScriptPage() {
      this.$router.push('/scriptView');
    },
    async resetData() {
      this.isResetting = true;
      this.resetMessage = '';
      try {
        await api.post('/reset');
        this.setupComplete = false;
        this.resetMessage = 'Data reset successfully.';
      } catch {
        this.resetMessage = 'Reset failed. Please try again.';
      }
    },
  }
};
</script>
