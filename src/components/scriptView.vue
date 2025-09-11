<template>
  <div class="container">
    <!-- Header -->
    <header class="header">
        <h1>Schedule Script for Birdnet</h1>
    </header>
    <!-- Form Body -->
    <main class="main-content">
        <div class="form-section">
            <!-- First Startup Section -->
            <div class="input-group">
                <label class="label">The script's first startup occurs at:</label>
                <div class="input-container">
                    <input type="date" v-model="startDate" class="form-input">
                    <input type="time" step="1" v-model="startTime" class="form-input">
                </div>
            </div>

            <!-- Continue Running Until Section -->
            <div class="input-group">
                <label class="label">The script will continue running until:</label>
                <div class="input-container">
                    <input type="date" v-model="endDate" class="form-input">
                    <input type="time" step="1" v-model="endTime" class="form-input">
                </div>
            </div>
        </div>
    </main>

    <!-- Buttons -->
    <footer class="footer">
        <div class="button-row">
            <button @click="addStates" class="button add-states-btn">Add States</button>
            <button @click="clearAllStates" class="button clear-states-btn">Clear All States</button>
        </div>
    </footer>

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
        startDate: this.localTime.split(' ')[0] || new Date().toISOString().slice(0, 10),
        startTime: this.localTime.split(' ')[1] || new Date().toTimeString().slice(0, 8),
        endDate: new Date().toISOString().slice(0, 10),
        endTime: new Date().toTimeString().slice(0, 8)
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

<style >

    .container {
        width: 100%;
        max-width: 48rem; /* 768px */
        background-color: var(--white);
        border-radius: 0.75rem; /* rounded-xl */
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* shadow-lg */
        overflow: hidden;
    }

    .header {
        background-color: var(--emerald-600);
        color: var(--white);
        padding: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top-left-radius: 0.75rem;
        border-top-right-radius: 0.75rem;
    }

    .header h1 {
        font-size: 2rem; /* text-xl */
        font-weight: 600; /* font-semibold */
    }

    .example-dropdown:hover {
        background-color: #f9fafb;
    }

    .example-dropdown:focus {
        outline: 2px solid transparent;
        outline-offset: 2px;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0), 0 0 0 2px var(--indigo-500);
        border-color: var(--indigo-500);
    }

    .main-content {
        padding: 1.5rem;
    }

    .form-section {
        display: flex;
        flex-direction: column;
        gap: 1.5rem; /* space-y-6 */
    }

    .input-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem; /* space-y-2 */
    }
    
    .input-container {
        display: flex;
        flex-direction: column;
        gap: 1rem; /* space-y-4 */
    }
    
    .label {
        display: block;
        color: var(--gray-700);
    }

    .form-input {
        flex: 1;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem; /* rounded-md */
        border: 1px solid var(--gray-300);
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); /* shadow-sm */
    }

    .form-input:focus {
        outline: 2px solid transparent;
        outline-offset: 2px;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0), 0 0 0 2px var(--indigo-500);
        border-color: var(--indigo-500);
    }

    .footer {
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        gap: 1rem; /* space-y-4 */
    }

    .button-row {
        display: flex;
        gap: 1rem; /* space-x-4 */
    }

    .button {
        padding: 0.5rem 1.5rem;
        border-radius: 0.375rem; /* rounded-md */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* shadow-md */
    }

    .add-states-btn {
        color: var(--white);
        background-color: var(--emerald-600);
    }
    
    .add-states-btn:hover {
        background-color: var(--emerald-700);
    }
    
    .clear-states-btn {
        color: var(--gray-700);
        background-color: var(--gray-200);
    }
    
    .clear-states-btn:hover {
        background-color: var(--gray-300);
    }

    .add-states-btn:focus {
        outline: 2px solid transparent;
        outline-offset: 2px;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0), 0 0 0 2px var(--emerald-500);
    }
    
    .clear-states-btn:focus{
        outline: 2px solid transparent;
        outline-offset: 2px;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0), 0 0 0 2px var(--gray-400);
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
