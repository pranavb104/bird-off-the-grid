<template>
  <div class="d-card p-6 max-w-md w-full">
    <DitherShadow />
    <h2 class="text-3xl font-bold text-[var(--color-text)] font-['IBM_Plex_Mono'] mb-2">BirdNet OffGrid</h2>
    <p class="text-lg text-[var(--color-text-secondary)] mb-4">Your Device is {{ socketStatus }}</p>
    <div class="d-input text-lg font-semibold text-[var(--color-text-secondary)] mb-6">
      {{ localTime }}
    </div>

    <button v-if="!setupComplete && socketStatus === 'Connected'" @click="goToScriptPage"
      class="d-btn text-xl">
      Setup →
    </button>

    <div v-if="setupComplete && socketStatus === 'Connected'" class="flex items-center justify-between gap-3">
      <button @click="$router.push('/dashboard')"
        class="d-btn text-xl cursor-pointer">
        Start →
      </button>
      <button @click="resetData" :disabled="isResetting"
        class="d-btn outline text-xl cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
        Reset
      </button>
    </div>

    <p v-if="resetMessage" class="text-[var(--color-text)] text-sm mt-3">{{ resetMessage }}</p>
  </div>
</template>

<script>
import api from '@/services/api';
import DitherShadow from '@/components/DitherShadow.vue';

export default {
  name: "setupView",
  components: { DitherShadow },
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
