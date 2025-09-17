<template>
  <div class="container">
    <!-- Header -->
    <h2>Schedule Your Script</h2>
    <!-- Form Body -->
    <main class="main-content">
        <div class="form-section">
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
        <br/>
        <br/>
        <button class="button" @click="addStates">Next -></button>
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
        endDate: new Date().toISOString().slice(0, 16)
    };
  },

  methods: {
    addStates() {
        // Placeholder for 'Add States' logic.
        // You would add your custom logic here to handle the form data.
        console.log('Add States button clicked!');
    },
    clearAllStates() {
        console.log('Clear All States button clicked!');

    },
    copyToClipboard() {

    },
  }
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
        padding: 1.5rem;
    }

    .form-section {
        display: flex;
        flex-direction: column;
        gap: 1.5rem; /* space-y-6 */
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
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #ced4da;
    }

    .button {
        background-color: #d63384;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 1.5rem;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .button:hover {
        background-color: #c61f6e;
    }

    /* Responsive Styles */
    @media (min-width: 640px) {
        .input-container {
            flex-direction: row;
            gap: 1rem; /* space-x-4 */
        }

        .footer {
            flex-direction: row;
        }
    }
    
</style>
