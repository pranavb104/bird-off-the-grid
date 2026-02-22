import api from '@/services/api';

export const getAudioUrl = (storedPath) => {
    if (!storedPath) return '';
    // storedPath = "detections/YYYY-MM-DD/Species_Name/file.mp3"
    const parts = storedPath.replace(/^detections\//, '').split('/');
    const [date, species, filename] = parts;
    const base = api.defaults.baseURL;
    return `${base}/audio/${encodeURIComponent(date)}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`;
};

export const getSpectrogramUrl = (storedPath) => {
    if (!storedPath) return '';
    const parts = storedPath.replace(/^detections\//, '').split('/');
    const [date, species, filename] = parts;
    const base = api.defaults.baseURL;
    return `${base}/spectrogram/${encodeURIComponent(date)}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`;
};
