<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h2>SnapSign</h2>
        <p>基于人脸识别的课堂自动点名系统</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" prefix-icon="User" />
        </el-form-item>

        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock"
            show-password />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-tips">
        <p>演示账号：admin / admin123（管理员）</p>
        <p>teacher01 / teacher123（教师） · student01 / student123（学生）</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import request from '../utils/request'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const { data } = await request.post('/api/v1/auth/login', {
      username: form.username,
      password: form.password,
    })

    // 持久化 Token 与用户信息
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('realName', data.real_name)

    ElMessage.success(`欢迎回来，${data.real_name}`)
    router.push('/')
  } catch (err: any) {
    const msg = err.response?.data?.detail || '登录失败，请检查网络'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 420px;
  padding: 40px 36px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #303133;
  letter-spacing: 2px;
}

.login-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.login-tips {
  margin-top: 16px;
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  line-height: 1.8;
}

.login-tips p {
  margin: 0;
}
</style>
