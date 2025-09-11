<template>
  <div id="app" class="container">
    <!-- Header -->
    <header class="header">
        <h1>Schedule Script Generator</h1>
        <div class="dropdown-container">
            <select class="example-dropdown">
                <option value="">Load an Example ...</option>
                <option value="example1">Example 1</option>
                <option value="example2">Example 2</option>
            </select>
        </div>
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
        <button @click="copyToClipboard" class="button copy-btn">Copy to Clipboard</button>
    </footer>

    <!-- Clipboard Message -->
    <div id="message-box" class="message-box">Copied to clipboard!</div>
  </div>
</template>

<script>
export default {
  name: 'scriptPage',

  data() {

  },

  methods: {
    addStates() {
        // Placeholder for 'Add States' logic.
        // You would add your custom logic here to handle the form data.
        console.log('Add States button clicked!');
    },
    clearAllStates() {
        const now = new Date();
        const date = now.toISOString().slice(0, 10);
        const time = now.toTimeString().slice(0, 8);
        this.startDate = date;
        this.startTime = time;
        this.endDate = date;
        this.endTime = time;
    },
    copyToClipboard() {
        // Create the "script" content to copy.
        const scriptContent = `Start: ${this.startDate}T${this.startTime}\nEnd: ${this.endDate}T${this.endTime}`;

        // Create a temporary textarea to hold the content to copy.
        const tempTextArea = document.createElement('textarea');
        tempTextArea.value = scriptContent;
        document.body.appendChild(tempTextArea);
        tempTextArea.select();

        // Use the deprecated but widely supported execCommand for clipboard access.
        try {
            document.execCommand('copy');
            this.showClipboardMessage();
        } catch (err) {
            console.error('Failed to copy text: ', err);
        } finally {
            document.body.removeChild(tempTextArea);
        }
    },
    showClipboardMessage() {
        const messageBox = document.getElementById('message-box');
        messageBox.classList.add('show');
        setTimeout(() => {
            messageBox.classList.remove('show');
        }, 2000); // Hide after 2 seconds
    }
  }
}
</script>

<style scoped>
    :root {
        --emerald-600: #059669;
        --emerald-700: #047857;
        --gray-700: #374151;
        --gray-200: #e5e7eb;
        --gray-300: #d1d5db;
        --white: #fff;
        --faint-gray: #f3f4f6;
        --indigo-500: #6366f1;
        --emerald-500: #10b981;
        --gray-400: #9ca3af;
        --clipboard-bg: #4CAF50;
    }

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
        font-size: 1.25rem; /* text-xl */
        font-weight: 600; /* font-semibold */
    }

    .dropdown-container {
        position: relative;
        display: inline-block;
    }

    .example-dropdown {
        border-radius: 0.375rem; /* rounded-md */
        border: 1px solid var(--gray-300);
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); /* shadow-sm */
        padding: 0.5rem 1rem;
        background-color: var(--white);
        color: var(--gray-700);
        width: 100%;
        cursor: pointer;
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
    
    .clear-states-btn, .copy-btn {
        color: var(--gray-700);
        background-color: var(--gray-200);
    }
    
    .clear-states-btn:hover, .copy-btn:hover {
        background-color: var(--gray-300);
    }

    .add-states-btn:focus {
        outline: 2px solid transparent;
        outline-offset: 2px;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0), 0 0 0 2px var(--emerald-500);
    }
    
    .clear-states-btn:focus, .copy-btn:focus {
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
    
    /* Custom styles for the clipboard message */
    .message-box {
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 10px 20px;
        background-color: var(--clipboard-bg);
        color: var(--white);
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        transition: opacity 0.5s ease-in-out;
        opacity: 0;
        pointer-events: none;
    }
    .message-box.show {
        opacity: 1;
    }
</style>
