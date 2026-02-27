import axios from 'axios';

const getBackendPort = () => {
    // If we're on a common frontend dev port, default to the backend port (8003)
    const currentPort = window.location.port;
    const isFrontendDev = ['5173', '5174', '5175', '5176', '5177', '5178', '5179', '3000', '3001'].includes(currentPort);

    if (isFrontendDev) return '8003';
    return currentPort || '8001';
};

export const BACKEND_PORT = getBackendPort();
const API_BASE_URL = `http://${window.location.hostname}:${BACKEND_PORT}/api`;

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const ocrService = {
    uploadFile: async (file, type) => {
        const formData = new FormData();
        formData.append('file', file);

        // Note: No leading slash here ensures it joins correctly with baseURL ending in /api
        return api.post(`process/upload?doc_type=${type}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    getStats: async () => {
        return api.get('stats');
    },

    getResults: async (docType = null) => {
        const params = docType ? { doc_type: docType } : {};
        return api.get('results', { params });
    },

    getPreviewUrl: (resultId) => {
        return `${API_BASE_URL}/results/${resultId}/preview`;
    },

    getDownloadUrl: (resultId) => {
        return `${API_BASE_URL}/results/${resultId}/docx/download`;
    },

    deleteResult: async (resultId) => {
        return api.delete(`results/${resultId}`);
    }
};

export const createWebSocket = (callback) => {
    const ws = new WebSocket(`ws://${window.location.hostname}:${BACKEND_PORT}/ws/batches`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        callback(data);
    };

    return ws;
};

export default api;
