<template>
  <div class="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
    <h2 class="text-3xl font-bold text-[#d63384] mb-2">BirdNet OffGrid</h2>
    <p class="text-lg text-gray-500 mb-4">Your Device is {{ socketStatus }}</p>
    <div class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300 mb-6">
      {{ localTime }}
    </div>

    <button v-if="!setupComplete && socketStatus === 'Connected'" @click="goToScriptPage"
      class="bg-[#d63384] hover:bg-[#c61f6e] text-white text-xl py-3 px-6 rounded-lg transition-colors">
      Setup ->
    </button>

    <div v-if="setupComplete && socketStatus === 'Connected'" class="flex items-center justify-between gap-3">
      <button @click="$router.push('/dashboard')"
        class="bg-[#d63384] hover:bg-[#c61f6e] text-white text-xl py-3 px-6 rounded-lg transition-colors cursor-pointer">
        Start ->
      </button>
      <button @click="resetData" :disabled="isResetting"
        class="bg-gray-200 hover:bg-gray-300 text-gray-700 text-xl py-3 px-6 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
        Reset
      </button>
    </div>

    <p v-if="resetMessage" class="text-green-600 text-sm mt-3">{{ resetMessage }}</p>
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
