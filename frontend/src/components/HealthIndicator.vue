<template>
  <div class="health-indicator" @click="cycleLabel">
    <div class="health-status">
      <span class="health-dot" :class="online ? 'online' : 'offline'"></span>
      <transition name="label-fade" mode="out-in">
        <span class="health-label" :key="currentLabel">{{ currentLabel }}</span>
      </transition>
    </div>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'HealthIndicator',
  data() {
    return {
      online: false,
      power: null,
      labelIndex: 0,
      pollId: null,
    };
  },
  computed: {
    labels() {
      const items = [this.online ? 'Online' : 'Offline'];
      if (this.power) {
        if (this.power.input_voltage != null)
          items.push(`Vin: ${this.power.input_voltage}V`);
        if (this.power.output_voltage != null)
          items.push(`Vout: ${this.power.output_voltage}V`);
        if (this.power.output_current != null)
          items.push(`I: ${this.power.output_current}A`);
      }
      return items;
    },
    currentLabel() {
      return this.labels[this.labelIndex] || this.labels[0];
    },
  },
  created() {
    this.fetchHealth();
    this.pollId = setInterval(this.fetchHealth, 10000);
  },
  beforeUnmount() {
    if (this.pollId) clearInterval(this.pollId);
  },
  methods: {
    async fetchHealth() {
      try {
        const { data } = await api.get('/health');
        this.online = data.status === 'ok';
        this.power = data.power || null;
      } catch {
        this.online = false;
        this.power = null;
      }
      if (this.labelIndex >= this.labels.length) {
        this.labelIndex = 0;
      }
    },
    cycleLabel() {
      this.labelIndex = (this.labelIndex + 1) % this.labels.length;
    },
  },
};
</script>

<style scoped>
.health-indicator {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 40;
  cursor: pointer;
  user-select: none;
  font-family: 'IBM Plex Mono', monospace;
}

.health-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.health-dot.online {
  background: #2d6a2e;
}

.health-dot.offline {
  background: var(--color-error);
}

.health-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.label-fade-enter-active,
.label-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.label-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.label-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
