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
        </div>
            <br/>
            <br/>
        <!-- Navigation Buttons -->
         <div v-if="state === 0">
            <button  class="button" @click="state = 1">Next</button>
         </div>
         <div v-if="state === 1">
            <button v-if="state === 1" class="button" @click="state = 0">Back</button>
            <span style="width: 25px; display: inline-block;"></span> 
            <button v-if="state === 1" class="button" @click="$router.push('/dashboard')">Next</button>
         </div>
         
    </main>

  </div>
</template>

<script>
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
    };
  },

  methods: {


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

    .selected-option {
        margin-top: 1rem;
        font-size: 1rem;
        font-style: italic;
        color: #c61f6e;
    }

    /* Responsive Styles */
    @media (min-width: 640px) {
        .input-container {
            flex-direction: row;
            gap: 1rem; /* space-x-4 */
        }
    }
    
</style>
