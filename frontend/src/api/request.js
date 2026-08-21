import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('userInfo')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    if (error.response?.status === 403) {
      return Promise.reject(error)
    }

    const detail = error.response?.data?.detail
    if (detail && typeof detail === 'string') {
      ElMessage.error(detail)
    } else if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else if (!error.response && error.message) {
      ElMessage.error('网络连接失败，请确认服务已启动')
    }

    return Promise.reject(error)
  }
)

export default request
