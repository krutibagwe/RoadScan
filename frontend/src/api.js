import axios from 'axios';

// Configure API
const API_BASE_URL = 'http://127.0.0.1:8000';
const API_TIMEOUT = 30000; // 30 seconds

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
});

// Request interceptor
api.interceptors.request.use((config) => {
  // Add auth token if needed
  // const token = localStorage.getItem('token');
  // if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * Uploads video with proper binary handling
 * @param {File} file - Video file to upload
 * @param {function} onProgress - Progress callback (0-100)
 */
export const uploadVideo = async (file, onProgress) => {
  try {
    const formData = new FormData();
    formData.append('video', file);  // Changed from 'file' to 'video' to match backend

    const response = await api.post('/upload/', formData, {  // Added trailing slash to match backend
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress?.(percent);
        }
      },
      timeout: 120000 // 2 minutes
    });

    return response.data;
  } catch (error) {
    const errorMessage = getErrorMessage(error);
    console.error('Upload failed:', {
      error: errorMessage,
      file: file.name,
      size: (file.size / (1024 * 1024)).toFixed(2) + 'MB'
    });
    throw new Error(errorMessage);
  }
};

/**
 * Search for license plates
 * @param {string} plateNumber - Plate number to search
 */
export const searchPlates = async (plateNumber) => {
  try {
    const response = await api.get(`/search/${encodeURIComponent(plateNumber)}`);
    return response.data;
  } catch (error) {
    const errorMessage = getErrorMessage(error);
    console.error('Search failed:', errorMessage);
    throw new Error(errorMessage);
  }
};

// Helper functions
const getErrorMessage = (error) => {
  return error.response?.data?.detail || 
         error.response?.data?.message || 
         error.message || 
         'Request failed';
};

const handleApiError = (error) => {
  const errorDetails = {
    message: error.message,
    status: error.response?.status,
    data: error.response?.data,
    config: error.config
  };
  
  console.error('API Error:', errorDetails);
  
  // Global error handling (e.g., redirect on 401)
  if (error.response?.status === 401) {
    // Handle unauthorized
  }
};

// Export configured instance
export default api;