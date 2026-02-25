import axios from 'axios';

// Default timeout for most requests (15 seconds)
const DEFAULT_TIMEOUT = 15000;

/**
 * Pre-configured axios instance for internal API calls.
 * Points to the BirdNET-Pi backend.
 */
const baseURL =
    process.env.VUE_APP_API_URL ||
    `http://${window.location.hostname}:7007/api`;

const api = axios.create({
    baseURL,
    timeout: DEFAULT_TIMEOUT,
    headers: {
        'Content-Type': 'application/json'
    }
});

export default api;
