import api from './index';

export const editorialBoardService = {
  getMembers: (role?: string) => 
    api.get(`/api/editorial-board/${role ? `?role=${role}` : ''}`),
    
  getMember: (id: string | number) => 
    api.get(`/api/editorial-board/${id}/`),
};