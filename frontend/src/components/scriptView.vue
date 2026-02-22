<template>
  <div class="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
    <!-- Header -->
    <h2 class="text-3xl font-bold text-[#d63384] mb-2">Schedule Your Script</h2>
    <!-- Form Body -->
    <main class="p-4">
        <div v-if="state === 0" class="flex flex-col gap-6">
            <!-- First Startup Section -->
            <div class="flex flex-col">
                <label class="text-lg text-gray-700">The first startup occurs at:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="datetime-local" v-model="startDate" class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300">
                </div>
            </div>
            <!-- Continue Running Until Section -->
            <div class="flex flex-col">
                <label class="text-lg text-gray-700">The script will run until:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="datetime-local" v-model="endDate" class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300">
                </div>
            </div>
        </div>
        <div v-if="state === 1" class="flex flex-col gap-6">
            <!-- Set on/off times -->
            <div class="flex flex-col">
                <label class="text-lg text-gray-700">Select on/off time:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <select class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300" v-model="selected">
                        <option v-for="option in options" :key="option.value" :value="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </div>
                <div class="mt-3 text-base italic text-[#c61f6e]"> {{ options.find(option => option.value === selected)?.info }}</div>
            </div>
            <!-- Custom time inputs shown only for option3 -->
            <div v-if="selected === 'option3'" class="flex flex-col">
                <label class="text-lg text-gray-700">On time:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="time" v-model="onTime" class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300">
                </div>
                <label class="text-lg text-gray-700" style="margin-top: 0.75rem;">Off time:</label>
                <div class="flex flex-col gap-2 mt-2">
                    <input type="time" v-model="offTime" class="text-lg font-semibold text-gray-600 bg-gray-100 px-5 py-2.5 rounded-lg border border-gray-300">
                </div>
            </div>
            <div v-if="submitError" class="text-red-500 text-sm mt-2">{{ submitError }}</div>
        </div>
            <br/>
            <br/>
        <!-- Navigation Buttons -->
         <div v-if="state === 0">
            <button class="bg-[#d63384] hover:bg-[#c61f6e] text-white text-xl py-3 px-6 rounded-lg transition-colors disabled:bg-[#e8a0c0] disabled:cursor-not-allowed" @click="state = 1">Next</button>
         </div>
         <div v-if="state === 1" class="flex items-center gap-6">
            <button class="bg-[#d63384] hover:bg-[#c61f6e] text-white text-xl py-3 px-6 rounded-lg transition-colors disabled:bg-[#e8a0c0] disabled:cursor-not-allowed" @click="state = 0">Back</button>
            <button class="bg-[#d63384] hover:bg-[#c61f6e] text-white text-xl py-3 px-6 rounded-lg transition-colors disabled:bg-[#e8a0c0] disabled:cursor-not-allowed" :disabled="isSubmitting" @click="submitSchedule">
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
