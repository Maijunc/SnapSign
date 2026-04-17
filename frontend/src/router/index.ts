// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { public: true },  // 标记为公开页，不需要登录
    },
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
    },
    {
      path: '/check_in',
      name: 'AttendanceCheck',
      component: () => import('../views/AttendanceCheck.vue')
    },
    {
      path: '/management',
      name: 'StudentManagement',
      component: () => import('../views/StudentManagement.vue')
    },
    {
      path: '/courses',
      name: 'MyCourses',
      component: () => import('../views/MyCourses.vue')
    }
  ]
})

// ========== 全局路由守卫：未登录一律拦截到 /login ==========
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.public) {
    // 公开页面直接放行（已登录的人访问 /login 则重定向回首页）
    token ? next('/') : next()
  } else {
    token ? next() : next('/login')
  }
})

export default router