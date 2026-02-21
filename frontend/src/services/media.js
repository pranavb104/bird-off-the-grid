import api from '@/services/api';

const getApiBaseUrl = () => {
    const base = api.defaults.baseURL;
    return base.endsWith('/') ? base.slice(0, -1) : base;
};

export const getAudioUrl = (filename) => {
    if (!filename) return '';
    // Adjust based on actual BirdNET-Pi static file serving
    return `${getApiBaseUrl().replace('/api', '')}/audio/${encodeURIComponent(filename)}`;
};

export const getSpectrogramUrl = (filename) => {
    if (!filename) return '';
    return `${getApiBaseUrl().replace('/api', '')}/spectrogram/${encodeURIComponent(filename)}`;
};
