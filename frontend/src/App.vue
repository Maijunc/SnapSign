<template>
  <!-- 登录页：全屏渲染，不带侧边栏 -->
  <router-view v-if="isLoginPage" />

  <!-- 业务页面：带侧边栏+顶栏的后台布局 -->
  <el-container v-else class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <span class="logo-text">SnapSign 考勤系统</span>
      </div>

      <el-menu router :default-active="$route.path" class="el-menu-vertical" background-color="#304156"
        text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <strong>基于人脸识别的课堂自动点名系统</strong>
        </div>
        <div class="header-right">
          <el-avatar size="small" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
          <span class="admin-name">{{ realName }} ({{ roleLabel }})</span>
          <el-button type="primary" text size="small" style="margin-left: 12px" @click="passwordDialogVisible = true">修改密码</el-button>
          <el-button type="danger" text size="small" style="margin-left: 4px" @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view></router-view>
      </el-main>
    </el-container>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
      <el-form :model="passwordForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="输入原密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPasswordChange" :loading="passwordSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, User, Camera, Check, Notebook, List, Setting, Reading, Calendar, DataAnalysis, Document, Finished } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from './utils/request'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login')

// 用 ref 存储身份信息，路由变化时自动刷新（解决切换账号不更新的问题）
const realName = ref(localStorage.getItem('realName') || '未知用户')
const currentRole = ref(localStorage.getItem('role') || '')

watch(() => route.path, () => {
  realName.value = localStorage.getItem('realName') || '未知用户'
  currentRole.value = localStorage.getItem('role') || ''
})

const roleMap: Record<string, string> = { admin: '管理员', teacher: '教师', student: '学生' }
const roleLabel = computed(() => roleMap[currentRole.value] || '未知')

// 全部菜单项定义，roles 标明哪些角色可见
const allMenuItems = [
  { path: '/',            label: '考勤数据大屏', icon: Monitor,  roles: ['admin', 'teacher'] },
  { path: '/check_in',    label: '课堂考勤打卡', icon: Check,    roles: ['teacher'] },
  { path: '/calendar',    label: '教学日历',     icon: Calendar, roles: ['teacher', 'student'] },
  { path: '/courses',     label: '我的课程',     icon: Notebook, roles: ['teacher'] },
  { path: '/approval',    label: '审批管理',     icon: Finished, roles: ['teacher'] },
  { path: '/student-dashboard', label: '考勤统计', icon: DataAnalysis, roles: ['student'] },
  { path: '/student-courses', label: '我的课程', icon: Notebook, roles: ['student'] },
  { path: '/my-attendance', label: '我的考勤',   icon: List,     roles: ['student'] },
  { path: '/leave-request', label: '请假申请',   icon: Document, roles: ['student'] },
  { path: '/register',    label: '人脸特征录入', icon: Camera,   roles: ['teacher', 'admin'] },
  { path: '/my-face',      label: '我的人脸',     icon: Camera,   roles: ['student'] },
  { path: '/class-students', label: '班级学生',   icon: Reading,  roles: ['teacher'] },
  { path: '/management',  label: '学生档案管理', icon: Reading,  roles: ['admin'] },
  { path: '/users',       label: '用户管理',     icon: User,     roles: ['admin'] },
  { path: '/course-admin', label: '课程管理',    icon: Setting,  roles: ['admin'] },
]

const menuItems = computed(() =>
  allMenuItems.filter(item => item.roles.includes(currentRole.value))
)

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.removeItem('realName')
  router.push('/login')
}

// 修改密码
const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const submitPasswordChange = async () => {
  if (!passwordForm.old_password || !passwordForm.new_password) return ElMessage.warning('请填写完整')
  if (passwordForm.new_password.length < 6) return ElMessage.warning('新密码至少6位')
  if (passwordForm.new_password !== passwordForm.confirm_password) return ElMessage.warning('两次输入的密码不一致')
  passwordSubmitting.value = true
  try {
    await request.put('/api/v1/auth/password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialogVisible.value = false
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    handleLogout()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '密码修改失败') }
  finally { passwordSubmitting.value = false }
}
</script>

<style>
/* 清除浏览器默认边距，让后台全屏铺满 */
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100vh;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 布局外层全屏 */
.layout-container {
  height: 100vh;
}

/* 深色侧边栏样式 */
.sidebar {
  background-color: #304156;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  z-index: 10;
}

/* Logo 区域 */
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  background-color: #2b3649;
  overflow: hidden;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  letter-spacing: 1px;
}

/* 去除菜单自带的难看边框 */
.el-menu-vertical {
  border-right: none;
}

/* 顶部白条 Header */
.header {
  background-color: #fff;
  color: #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 21, 41, .08);
  padding: 0 20px;
  z-index: 9;
}

.header-right {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.admin-name {
  margin-left: 10px;
  font-size: 14px;
  color: #606266;
}

/* 灰色主背景 */
.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.card-header {
  font-weight: bold;
  font-size: 16px;
}

.card-body {
  color: #666;
  line-height: 1.8;
}

/* 修正按钮内图标+文字垂直居中 */
.el-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>