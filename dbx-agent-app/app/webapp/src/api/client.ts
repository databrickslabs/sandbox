import axios, { AxiosInstance, AxiosError } from 'axios'

const registryClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_REGISTRY_API_URL || '/api',
  timeout: 30000,
  withCredentials: true, // Enable cookie-based auth for production API
  headers: {
    'Content-Type': 'application/json'
  }
})

const supervisorClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_SUPERVISOR_URL || '/api',
  timeout: 60000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

registryClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('databricks_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

registryClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear invalid token and let the caller handle auth failure
      localStorage.removeItem('databricks_token')
    }
    return Promise.reject(error)
  }
)

supervisorClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('databricks_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

supervisorClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear invalid token and let the caller handle auth failure
      localStorage.removeItem('databricks_token')
    }
    return Promise.reject(error)
  }
)

export { registryClient, supervisorClient }
