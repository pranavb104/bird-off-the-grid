<template>
  <div class="container">
    <!-- Header -->
    <h2>Schedule Your Script</h2>
    <!-- Form Body -->
    <main class="main-content">
        <div v-if="state === 0" class="form-section">
            <!-- First Startup Section -->
            <div class="input-group">
                <label class="label">The first startup occurs at:</label>
                <div class="input-container">
                    <input type="datetime-local" v-model="startDate" class="form-input">
                </div>
            </div>
            <!-- Continue Running Until Section -->
            <div class="input-group">
                <label class="label">The script will run until:</label>
                <div class="input-container">
                    <input type="datetime-local" v-model="endDate" class="form-input">
                </div>
            </div>
        </div>
        <div v-if="state === 1" class="form-section">
            <!-- Set on/off times -->
            <div class="input-group">
                <label class="label">Select on/off time:</label>
                <div class="input-container">
                    <select class="form-input" v-model="selected">
                        <option v-for="option in options" :key="option.value" :value="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </div>
                <div class="selected-option"> {{ options.find(option => option.value === selected)?.info }}</div>
            </div>
            <!-- Custom time inputs shown only for option3 -->
            <div v-if="selected === 'option3'" class="input-group">
                <label class="label">On time:</label>
                <div class="input-container">
                    <input type="time" v-model="onTime" class="form-input">
                </div>
                <label class="label" style="margin-top: 0.75rem;">Off time:</label>
                <div class="input-container">
                    <input type="time" v-model="offTime" class="form-input">
                </div>
            </div>
            <div v-if="submitError" class="error-message">{{ submitError }}</div>
        </div>
            <br/>
            <br/>
        <!-- Navigation Buttons -->
         <div v-if="state === 0">
            <button class="button" @click="state = 1">Next</button>
         </div>
         <div v-if="state === 1">
            <button class="button" @click="state = 0">Back</button>
            <span style="width: 25px; display: inline-block;"></span>
            <button class="button" :disabled="isSubmitting" @click="submitSchedule">
                {{ isSubmitting ? 'Submitting...' : 'Next' }}
            </button>
         </div>

    </main>

  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'scriptPage',
  props: {
    localTime: String,
    socketStatus: String
  },

  data() {
    return {
        startDate: new Date().toISOString().slice(0, 16),
        endDate: new Date().toISOString().slice(0, 16),
        state: 0,
        options: [
            { text: 'Dawn / Dusk', value: 'option1', info: "Script runs for an hour during Dawn (5:00 AM - 6:00 AM) & Dusk (6:00 PM - 7:00 PM)" },
            { text: 'Morning / Afternoon', value: 'option2', info: "Script runs an hour during Morning (8:00 AM - 9:00 AM) & Afternoon (4:00 PM - 5:00 PM)" },
            { text: 'Custom Time', value: 'option3', info: "Script runs at your specified times." }
        ],
        selected: 'option3',
        onTime: '07:00',
        offTime: '08:00',
        isSubmitting: false,
        submitError: null,
    };
  },

  methods: {
    async submitSchedule() {
        if (!this.startDate || !this.endDate) {
            this.submitError = 'Please set both start and end dates.';
            return;
        }
        if (this.selected === 'option3' && (!this.onTime || !this.offTime)) {
            this.submitError = 'Please set both on and off times for custom schedule.';
            return;
        }

        const scheduleTypeMap = {
            option1: 'dawn_dusk',
            option2: 'morning_afternoon',
            option3: 'custom',
        };

        const body = {
            start_datetime: this.startDate,
            end_datetime: this.endDate,
            schedule_type: scheduleTypeMap[this.selected],
        };

        if (this.selected === 'option3') {
            body.on_time = this.onTime;
            body.off_time = this.offTime;
        }

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

    .container {
        background: #fff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        max-width: 500px;
        width: 100%;
    }

    h2 {
        font-size: 2rem;
        color: #d63384;
        margin-bottom: 0.5rem;

    }

    .main-content {
        padding: 1rem;
    }

    .form-section {
        display: flex;
        flex-direction: column;
        gap: 1.5rem; /* space-y-6 */
    }

    .input-container {
        display: flex;
        flex-direction: column;
        gap: 0.5rem; /* space-y-2 */
        margin-top: 0.5rem;
    }

    .label {
        font-size: 1.25rem; /* text-lg */
        display: block;
        color: var(--gray-700);
    }

    .form-input {
        font-size: 1.125rem;
        font-weight: 600;
        color: #495057;
        background-color: #e9ecef;
        margin-top: 0.3rem;
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #ced4da;
    }

    .button {
        background-color: #d63384;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 1.25rem;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .button:hover {
        background-color: #c61f6e;
    }
    .button:disabled {
        background-color: #e8a0c0;
        cursor: not-allowed;
    }

    .selected-option {
        margin-top: 1rem;
        font-size: 1rem;
        font-style: italic;
        color: #c61f6e;
    }

    .error-message {
        color: #dc3545;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }

    /* Responsive Styles */
    @media (min-width: 640px) {
        .input-container {
            flex-direction: row;
            gap: 1rem; /* space-x-4 */
        }
    }

</style>
