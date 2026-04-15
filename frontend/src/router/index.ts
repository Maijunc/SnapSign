// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: Dashboard
    },
    {
      path: '/register',
      name: 'FaceRegister',
      // 懒加载模式：只有点进这个页面才会加载摄像头相关代码
      component: () => import('../views/FaceRegistration.vue')
    }
  ]
})

export default router