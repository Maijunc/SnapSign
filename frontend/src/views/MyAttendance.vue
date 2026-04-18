<template>
  <div class="my-attendance-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📋 我的考勤记录</span>
          <el-button type="primary" icon="Refresh" @click="fetchRecords" :loading="isLoading" size="small">
            刷新
          </el-button>
        </div>
      </template>

      <el-empty v-if="!isLoading && records.length === 0" description="暂无考勤记录，请先完成人脸录入并参与考勤打卡" />

      <el-table v-else :data="records" v-loading="isLoading" stripe border style="width: 100%">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column label="签到时间" width="200">
          <template #default="{ row }">
            {{ formatTime(row.check_in_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'present' ? 'success' : row.status === 'late' ? 'warning' : 'danger'"
              size="small"
            >
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="匹配距离" width="120" align="center">
          <template #default="{ row }">
            {{ row.face_distance?.toFixed(3) ?? '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const records = ref<any[]>([])
const isLoading = ref(false)

const fetchRecords = async () => {
  isLoading.value = true
  try {
    const res = await request.get('/api/v1/attendance/my')
    records.value = res.data
  } catch {
    ElMessage.error('获取考勤记录失败')
  } finally {
    isLoading.value = false
  }
}

const statusText = (s: string) => ({ present: '已到', late: '迟到', absent: '缺勤' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

onMounted(() => fetchRecords())
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
</style>
