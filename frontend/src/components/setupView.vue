<template>
  <div class="container">
        <h2>BirdNet OffGrid</h2>
        <p class="message">Your Device is {{ socketStatusText }}</p>
        <div class="time-display"> {{ localTime }} </div>
        <br/>
        <br/>
        <button v-if="socketStatus === 'Connected'" class="send-button" v-on:click="goToScriptPage">Setup -></button>
  </div>
</template>

<script>
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
      receivedMessage: null
    };
  },

    computed: {
        socketStatusText() {
            return this.socketStatus;
        }
    },

    methods: {
      // Function to navigate to the script page.
      goToScriptPage() {
        this.$router.push('/scriptView');
      },
    }
};
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
    .message {
      font-size: 1.25rem;
      color: #666;
      margin-bottom: 2rem;
    }
    .time-display {
      font-size: 1.125rem;
      font-weight: 600;
      color: #495057;
      background-color: #e9ecef;
      padding: 10px 20px;
      border-radius: 8px;
      border: 1px solid #ced4da;
  }

  .send-button {
      background-color: #d63384;
      color: white;
      border: none;
      padding: 12px 24px;
      font-size: 1.25rem;
      border-radius: 8px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    .send-button:hover {
      background-color: #c61f6e;
    }
</style>