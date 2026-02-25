<template>
  <div id="app">
    <div v-if="$route.path === '/'" class="setupView">
      <setupView  :localTime="localTime" :socketStatus="socketStatus"/>
    </div>
    <div v-if="$route.path === '/scriptView'" class="scriptView">
      <scriptView :localTime="localTime" :socketStatus="socketStatus"/>
    </div>
    <div v-if="$route.path === '/dashboard'" class="dashboardView">
      <Dashboard />
    </div>
  </div>
</template>

<script>
import setupView from './components/setupView.vue';
import scriptView from './components/scriptView.vue';
import Dashboard from './components/Dashboard.vue';

export default {
  name: 'bird-off-the-grid',
  components: {
    setupView,
    scriptView,
    Dashboard
  },

  data() {
    return {
      counter:0,
      socket: null, // The WebSocket object.
      localTime: null, //localTime
      socketStatus: "disconnected" , //socket statuss
      };
    },

    // The mounted lifecycle hook runs after the component has been mounted to the DOM.
    mounted() {
      // Set up an interval to update the time every second.
      this.intervalId = setInterval(() => {
          if (this.socket.readyState === WebSocket.OPEN) {
              const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
              this.localTime = new Date().toLocaleDateString('en-US', options);
          }
      }, 1000);

      //reconnect interval for websocket
      this.reconInterval = setInterval(() => {
          if (this.socket.readyState !== WebSocket.OPEN) {
              console.log('WebSocket is not open. Attempting to reconnect...');
              this.initializeWebSocket();
          }
      }, 5000); // Check every 5 seconds

    },

    // The created lifecycle hook runs after the instance is created.
    created() {
      this.setLocalTime();
      this.initializeWebSocket();
    },

    methods: {

      // Function to set the local time in the desired format.
      setLocalTime() {
        const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        this.localTime = new Date().toLocaleDateString('en-US', options);
      },

      // Function to initialize the WebSocket connection and set up event handlers.
      initializeWebSocket() {
        const wsUrl =
            process.env.VUE_APP_WS_URL ||
            `ws://${window.location.hostname}:7007/ws`;
        this.socket = new WebSocket(wsUrl);

        // Event handler for when the connection is established.
        this.socket.onopen = () => {
          this.socketStatus = 'Connected';
          this.setLocalTime();
          this.socket.send(this.localTime); // Send the current time to the server upon connection.
          console.log('WebSocket connection established.');
        };

        // Event handler for when a message is received from the server.
        this.socket.onmessage = event => {
          this.receivedMessage = event.data;
          console.log('Message received:', this.receivedMessage);
        };

        // Event handler for connection errors.
        this.socket.onerror = error => {
          this.socketStatus = 'Error';
          console.error('WebSocket error:', error);
        };

        // Event handler for when the connection is closed.
        this.socket.onclose = () => {
          this.socketStatus = 'Disconnected';
          console.log('WebSocket connection closed.');
        };
      } 
    },

    // It's crucial to clear the timer here to avoid memory leaks.
    beforeUnmount() {
      // Clear the interval using the ID we stored earlier.
      if (this.intervalId) {
        clearInterval(this.intervalId);
      }

      //Close the WebSocket connection cleanly.
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.close();
        console.log('WebSocket connection is being closed.');
      }
    }
    
}
</script>

<style>

  /* Global Styles */
  #app {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    margin: 0px;
    background: url(assets/bird-bkg.png);
    background-repeat: no-repeat ;
    background-size: cover;
    min-height: 100vh;
    overflow-y: auto;
  }

  .setupView {
      /* font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; */
      display: flex;
      justify-content: center;
      align-items: center; 
      min-height: 100vh;
      text-align: center;
      padding: 20px;
    }

  .scriptView {
    /* font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; */
    display: flex;
    justify-content: center;
    align-items: center; 
    min-height: 100vh;
    text-align: center;
    padding: 20px;
}

  .dashboardView {
    min-height: 100vh;
    padding: 12px;
    background-color: #f3f4f6; /* light gray background */
  }

  @media (min-width: 1024px) {
    .dashboardView {
      padding: 20px;
    }
  }
</style>
