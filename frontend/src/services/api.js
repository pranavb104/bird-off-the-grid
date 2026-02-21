import axios from 'axios';

// Default timeout for most requests (15 seconds)
const DEFAULT_TIMEOUT = 15000;

/**
 * Pre-configured axios instance for internal API calls.
 * Points to the BirdNET-Pi backend.
 */
const api = axios.create({
    baseURL: 'http://192.168.1.203:7100/api', // Assuming backend is on port 7100/api based on websocket
    timeout: DEFAULT_TIMEOUT,
    headers: {
        'Content-Type': 'application/json'
    }
});

export default api;
