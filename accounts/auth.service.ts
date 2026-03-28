import api from './index';

export const authService = {
  getMe: () => api.get('/api/me'),
  
  login: (data: any) => api.post('/api/auth/login', data),
  
  verifyEmail: (token: string) => api.get(`/api/auth/verify-email?token=${token}`),
};