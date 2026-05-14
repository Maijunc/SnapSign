// src/utils/request.ts
// axios 封装：自动注入 JWT Token + 401 自动跳转登录页

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 30000,
})

// ========== 请求拦截：注入 Token ==========
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ========== 响应拦截：处理 401 ==========
request.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    const isLoginRequest = typeof url === 'string' && url.includes('/api/v1/auth/login')

    if (status === 401 && !isLoginRequest) {
      // Token 过期或无效，清除本地状态，跳转登录页
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('realName')
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request
