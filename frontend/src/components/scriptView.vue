<template>
  <div class="d-card p-6 max-w-md w-full">
    <DitherShadow />
    <!-- Header -->
    <h2 class="text-3xl font-bold text-[var(--color-text)] font-['IBM_Plex_Mono'] mb-2">Schedule Your Script</h2>
    <!-- Form Body -->
    <main class="p-4">
        <div v-if="state === 0" class="flex flex-col gap-6">
            <!-- First Startup Section -->
            <div class="flex flex-col">
                <label class="text-lg text-[var(--color-text-secondary)]">The first startup occurs at:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="datetime-local" v-model="startDate" class="d-input text-lg">
                </div>
            </div>
            <!-- Continue Running Until Section -->
            <div class="flex flex-col">
                <label class="text-lg text-[var(--color-text-secondary)]">The script will run until:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="datetime-local" v-model="endDate" class="d-input text-lg">
                </div>
            </div>
        </div>
        <div v-if="state === 1" class="flex flex-col gap-5">
            <div class="flex flex-col">
                <label class="text-lg text-[var(--color-text-secondary)] mb-2">Daily on-time slots:</label>
                <span class="offgrid-note">Off-grid limit: max 4 hours of runtime per day</span>
            </div>

            <div class="flex flex-col gap-3">
                <div
                    v-for="(slot, idx) in slots"
                    :key="idx"
                    class="slot-row"
                >
                    <button
                        type="button"
                        class="slot-add"
                        :class="{ invisible: !(idx === slots.length - 1 && slots.length < 3) }"
                        @click="addSlot"
                        aria-label="Add time slot"
                    >+</button>
                    <span class="slot-label">Turn on</span>
                    <select v-model.number="slot.hour" class="slot-select">
                        <option v-for="h in hourOptions" :key="h" :value="h">{{ String(h).padStart(2, '0') }}hr</option>
                    </select>
                    <span class="slot-label">for</span>
                    <select v-model.number="slot.duration" class="slot-select">
                        <option v-for="d in durationOptions" :key="d" :value="d">{{ d }}h</option>
                    </select>
                    <button
                        type="button"
                        class="slot-remove"
                        :class="{ invisible: slots.length === 1 }"
                        @click="removeSlot(idx)"
                        :aria-label="`Remove slot ${idx + 1}`"
                    >×</button>
                </div>
            </div>

            <div class="flex items-center justify-end">
                <span class="text-sm font-['IBM_Plex_Mono'] text-[var(--color-text-secondary)]">
                    Total: {{ totalHours }}h / 4h
                </span>
            </div>

            <div v-if="submitError" class="text-[var(--color-error)] text-sm">{{ submitError }}</div>
        </div>
            <br/>
            <br/>
        <!-- Navigation Buttons -->
         <div v-if="state === 0">
            <button class="d-btn text-xl" @click="state = 1">Next</button>
         </div>
         <div v-if="state === 1" class="flex items-center justify-between gap-6">
            <button class="d-btn outline text-xl" @click="state = 0">Back</button>
            <button class="d-btn text-xl disabled:opacity-50 disabled:cursor-not-allowed" :disabled="isSubmitting" @click="submitSchedule">
                {{ isSubmitting ? 'Submitting...' : 'Submit' }}
            </button>
         </div>

    </main>

  </div>
</template>

<script>
import api from '@/services/api';
import DitherShadow from '@/components/DitherShadow.vue';

export default {
  name: 'scriptPage',
  components: { DitherShadow },
  props: {
    localTime: String,
    socketStatus: String
  },

  data() {
    return {
        startDate: new Date().toISOString().slice(0, 16),
        endDate: new Date().toISOString().slice(0, 16),
        state: 0,
        hourOptions: Array.from({ length: 23 }, (_, i) => i + 1),  // 1..23
        durationOptions: [1, 2, 3],
        slots: [{ hour: 6, duration: 1 }],
        isSubmitting: false,
        submitError: null,
    };
  },

  computed: {
    totalHours() {
        return this.slots.reduce((sum, s) => sum + (s.duration || 0), 0);
    },
  },

  methods: {
    addSlot() {
        if (this.slots.length >= 3) return;
        this.slots.push({ hour: 12, duration: 1 });
    },
    removeSlot(idx) {
        if (this.slots.length <= 1) return;
        this.slots.splice(idx, 1);
    },
    validateSlots() {
        if (this.slots.length === 0) return 'Add at least one time slot.';
        if (this.totalHours > 4) return 'Total runtime exceeds the 4-hour daily limit.';

        const sorted = [...this.slots].sort((a, b) => a.hour - b.hour);
        for (let i = 0; i < sorted.length; i++) {
            const s = sorted[i];
            if (s.hour + s.duration > 24) {
                return `Slot starting at ${String(s.hour).padStart(2, '0')}:00 for ${s.duration}h goes past midnight.`;
            }
            if (i > 0) {
                const prev = sorted[i - 1];
                const gap = s.hour - (prev.hour + prev.duration);
                if (gap < 1) {
                    return 'Slots must be at least 1 hour apart.';
                }
            }
        }
        return null;
    },
    async submitSchedule() {
        if (!this.startDate || !this.endDate) {
            this.submitError = 'Please set both start and end dates.';
            return;
        }

        const slotError = this.validateSlots();
        if (slotError) {
            this.submitError = slotError;
            return;
        }

        const body = {
            start_datetime: this.startDate,
            end_datetime: this.endDate,
            slots: this.slots.map(s => ({ hour: s.hour, duration: s.duration })),
        };

        this.isSubmitting = true;
        this.submitError = null;
        try {
            await api.post('/schedule', body);
            this.$router.push('/dashboard');
        } catch (e) {
            this.submitError = e.response?.data?.error || 'Failed to submit schedule. Please try again.';
        } finally {
            this.isSubmitting = false;
        }
    },
  },

}
</script>

<style scoped>
.offgrid-note {
    display: inline-block;
    align-self: flex-start;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: var(--color-primary);
    color: var(--color-card);
    padding: 4px 8px;
    border-radius: 2px;
}

.slot-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
}

.slot-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-text);
    white-space: nowrap;
}

.slot-select {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    font-weight: 500;
    background: var(--color-card);
    color: var(--color-text);
    border: 1.5px solid var(--color-border);
    border-radius: 2px;
    padding: 6px 8px;
    outline: none;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%230a0a0a' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 22px;
}

.slot-remove,
.slot-add {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.1rem;
    line-height: 1;
    width: 26px;
    height: 26px;
    background: var(--color-card);
    color: var(--color-primary);
    border: 1.5px solid var(--color-border);
    border-radius: 2px;
    cursor: pointer;
    flex-shrink: 0;
}

.slot-remove {
    margin-left: auto;
}

.slot-remove:hover,
.slot-add:hover {
    background: var(--color-primary);
    color: var(--color-card);
}

.slot-remove.invisible,
.slot-add.invisible {
    visibility: hidden;
}

.d-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
</style>
