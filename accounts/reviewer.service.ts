import api from './index';

export const reviewerService = {
  getAssignments: () => 
    api.get('/api/reviewer/assignments/'),
    
  getAssignment: (id: string | number) => 
    api.get(`/api/reviewer/assignments/${id}/`),
    
  acceptAssignment: (id: string | number) => 
    api.post(`/api/reviewer/assignments/${id}/accept/`),
    
  declineAssignment: (id: string | number) => 
    api.post(`/api/reviewer/assignments/${id}/decline/`),
    
  submitReview: (id: string | number, data: any) => 
    api.post(`/api/reviewer/assignments/${id}/submit-review/`, data),
    
  getInvitationByToken: (token: string) => 
    api.get(`/api/reviewer/accept-by-token/?token=${token}`),
    
  acceptByToken: (token: string) => 
    api.post('/api/reviewer/accept-by-token/', { token }),
};