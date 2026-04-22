// EdgeHunter — API Service Layer
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
});

// Response interceptor para logging
api.interceptors.response.use(
  res => res.data,
  err => {
    console.error('[API Error]', err.response?.status, err.config?.url);
    return Promise.reject(err);
  }
);

// ======================== BETS ========================
export const BetsAPI = {
  getAll: (params = {}) => api.get('/bets/', { params }),
  getPending: () => api.get('/bets/pending'),
  getStats: (days = 30) => api.get('/bets/stats', { params: { days } }),
  getCLV: (days = 30) => api.get('/bets/clv', { params: { days } }),
  getById: (id) => api.get(`/bets/${id}`),
};

// ======================== GAMES ========================
export const GamesAPI = {
  getAll: (params = {}) => api.get('/games/', { params }),
  getUpcoming: () => api.get('/games/upcoming'),
  getById: (id) => api.get(`/games/${id}`),
  predict: (id) => api.post(`/games/${id}/predict`),
  getLeagues: () => api.get('/games/leagues'),
};

// ======================== ANALYTICS ========================
export const AnalyticsAPI = {
  getOverview: (days = 30) => api.get('/analytics/overview', { params: { days } }),
  getROITimeline: (days = 30) => api.get('/analytics/roi-timeline', { params: { days } }),
  getROIByLeague: (days = 30) => api.get('/analytics/roi-by-league', { params: { days } }),
  getEdgeDistribution: () => api.get('/analytics/edge-distribution'),
};

// ======================== MODELS ========================
export const ModelsAPI = {
  getAll: () => api.get('/models/'),
  getActive: () => api.get('/models/active'),
  getWeights: () => api.get('/models/weights'),
  getDrift: () => api.get('/models/drift'),
  triggerTrain: () => api.post('/models/train'),
};

export default api;
