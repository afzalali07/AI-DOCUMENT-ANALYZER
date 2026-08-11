import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  || `${window.location.protocol}//${window.location.hostname}:8000/api`;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const apiService = {
  // Health Check
  getHealth: async () => {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      console.error('Error fetching health status:', error);
      return {
        status: 'offline',
        services: { sqlite: 'failed', chromadb: 'failed', gemini_api: 'disconnected' },
        chroma_chunk_count: 0
      };
    }
  },

  // Document Endpoints
  uploadDocuments: async (files, useOcr = false) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post(`${API_BASE_URL}/documents/upload`, formData, {
        params: { use_ocr: useOcr },
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 10 * 60 * 1000,
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading documents:', error);
      throw error.response?.data?.detail || 'Error uploading files';
    }
  },

  listDocuments: async () => {
    try {
      const response = await apiClient.get('/documents');
      return response.data;
    } catch (error) {
      console.error('Error listing documents:', error);
      throw error.response?.data?.detail || 'Error listing documents';
    }
  },

  getDocumentSummary: async (docId) => {
    try {
      const response = await apiClient.get(`/documents/${docId}/summary`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching summary for document ${docId}:`, error);
      throw error.response?.data?.detail || 'Error fetching summary';
    }
  },

  deleteDocument: async (docId) => {
    try {
      const response = await apiClient.delete(`/documents/${docId}`);
      return response.data;
    } catch (error) {
      console.error(`Error deleting document ${docId}:`, error);
      throw error.response?.data?.detail || 'Error deleting document';
    }
  },

  // Chat Endpoints
  listSessions: async () => {
    try {
      const response = await apiClient.get('/chat/sessions');
      return response.data;
    } catch (error) {
      console.error('Error listing sessions:', error);
      throw error.response?.data?.detail || 'Error listing chat sessions';
    }
  },

  createSession: async (title = 'New Chat') => {
    try {
      const response = await apiClient.post('/chat/sessions', null, {
        params: { title },
      });
      return response.data;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error.response?.data?.detail || 'Error creating chat session';
    }
  },

  getSessionHistory: async (sessionId) => {
    try {
      const response = await apiClient.get(`/chat/sessions/${sessionId}/history`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching chat history for ${sessionId}:`, error);
      throw error.response?.data?.detail || 'Error fetching chat history';
    }
  },

  deleteSession: async (sessionId) => {
    try {
      const response = await apiClient.delete(`/chat/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error(`Error deleting session ${sessionId}:`, error);
      throw error.response?.data?.detail || 'Error deleting chat session';
    }
  },

  askQuestion: async (query, sessionId = null, documentIds = null) => {
    try {
      const payload = {
        query,
        session_id: sessionId,
        document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
      };
      const response = await apiClient.post('/chat/', payload);
      return response.data;
    } catch (error) {
      console.error('Error querying RAG:', error);
      throw error.response?.data?.detail || 'Error processing your question';
    }
  },

  regenerateSummary: async (docId) => {
    try {
      const response = await apiClient.post(`/documents/${docId}/regenerate`);
      return response.data;
    } catch (error) {
      console.error(`Error regenerating summary for ${docId}:`, error);
      throw error.response?.data?.detail || 'Error regenerating summary';
    }
  },
};
export default apiService;
