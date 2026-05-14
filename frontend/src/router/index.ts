// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

// 各角色的默认首页
const roleHomePage: Record<string, string> = {
  admin: '/',
  teacher: '/calendar',
  student: '/student-dashboard',
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'Dashboard',
      component: Dashboard,
      meta: { roles: ['admin', 'teacher'] },
    },
    {
      path: '/register',
      name: 'FaceRegister',
      component: () => import('../views/FaceRegistration.vue'),
      meta: { roles: ['teacher', 'admin'] },
    },
    {
      path: '/my-face',
      name: 'MyFaceRegister',
      component: () => import('../views/MyFaceRegistration.vue'),
      meta: { roles: ['student'] },
    },
    {
      path: '/check_in',
      name: 'AttendanceCheck',
      component: () => import('../views/AttendanceCheck.vue'),
      meta: { roles: ['teacher'] },
    },
    {
      path: '/management',
      name: 'StudentManagement',
      component: () => import('../views/StudentManagement.vue'),
      meta: { roles: ['admin'] },
    },
    {
      path: '/class-students',
      name: 'ClassStudents',
      component: () => import('../views/ClassStudents.vue'),
      meta: { roles: ['teacher'] },
    },
    {
      path: '/approval',
      name: 'ApprovalManagement',
      component: () => import('../views/ApprovalManagement.vue'),
      meta: { roles: ['teacher'] },
    },
    {
      path: '/courses',
      name: 'MyCourses',
      component: () => import('../views/MyCourses.vue'),
      meta: { roles: ['teacher'] },
    },
    {
      path: '/student-courses',
      name: 'StudentCourses',
      component: () => import('../views/StudentCourses.vue'),
      meta: { roles: ['student'] },
    },
    {
      path: '/my-attendance',
      name: 'MyAttendance',
      component: () => import('../views/MyAttendance.vue'),
      meta: { roles: ['student'] },
    },
    {
      path: '/leave-request',
      name: 'LeaveRequest',
      component: () => import('../views/LeaveRequest.vue'),
      meta: { roles: ['student'] },
    },
    {
      path: '/student-dashboard',
      name: 'StudentDashboard',
      component: () => import('../views/StudentDashboard.vue'),
      meta: { roles: ['student'] },
    },
    {
      path: '/users',
      name: 'UserManagement',
      component: () => import('../views/UserManagement.vue'),
      meta: { roles: ['admin'] },
    },
    {
      path: '/course-admin',
      name: 'CourseManagement',
      component: () => import('../views/CourseManagement.vue'),
      meta: { roles: ['admin'] },
    },
    {
      path: '/calendar',
      name: 'TeachingCalendar',
      component: () => import('../views/TeachingCalendar.vue'),
      meta: { roles: ['teacher', 'student'] },
    },
  ]
})

// ========== 全局路由守卫：登录校验 + 角色校验 ==========
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role') || ''

  // 公开页面
  if (to.meta.public) {
    return token ? next(roleHomePage[role] || '/') : next()
  }

  // 未登录
  if (!token) return next('/login')

  // 角色校验
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && !allowedRoles.includes(role)) {
    // 无权限，跳转到自己角色的首页
    return next(roleHomePage[role] || '/')
  }

  next()
})

export default router