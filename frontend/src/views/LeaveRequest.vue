<template>
  <div class="leave-request-container">
    <el-row :gutter="20">
      <!-- 提交请假 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header><span style="font-weight: bold;">📝 提交请假</span></template>

          <el-form label-width="80px" @submit.prevent>
            <el-form-item label="选择课程">
              <el-select v-model="selectedCourseId" placeholder="请选择课程" clearable style="width: 100%;" @change="onCourseChange">
                <el-option v-for="c in courseOptions" :key="c.course_id" :label="c.course_name + ' (' + c.class_name + ')'" :value="c.course_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="选择排课">
              <el-select v-model="leaveForm.schedule_id" placeholder="请选择具体排课" style="width: 100%;" :disabled="scheduleOptions.length === 0" @change="leaveForm.leave_date = ''">
                <el-option v-for="s in scheduleOptions" :key="s.schedule_id" :label="weekdayText(s.weekday) + ' ' + s.start_time + '-' + s.end_time + (s.location ? ' ' + s.location : '')" :value="s.schedule_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="请假日期">
              <el-date-picker v-model="leaveForm.leave_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%;" :disabled-date="disabledDate" :disabled="!leaveForm.schedule_id" class="leave-date-picker" />
            </el-form-item>
            <el-form-item label="请假理由">
              <el-input v-model="leaveForm.reason" type="textarea" :rows="3" placeholder="请说明请假理由（如身体不适、家中急事等）" maxlength="500" show-word-limit />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitLeave" :loading="submitting" style="width: 100%;">提交请假</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 请假记录 -->
      <el-col :span="14">
        <el-card shadow="hover" v-loading="loading">
          <template #header>
            <div class="card-header">
              <span style="font-weight: bold;">📋 我的请假记录</span>
              <el-button type="primary" icon="Refresh" @click="fetchLeaves" size="small" :loading="loading">刷新</el-button>
            </div>
          </template>

          <el-empty v-if="!loading && leaves.length === 0" description="暂无请假记录" />

          <el-table v-else :data="leaves" stripe border style="width: 100%">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="course_name" label="课程" min-width="120" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column prop="leave_date" label="请假日期" width="120" />
            <el-table-column prop="reason" label="理由" min-width="150" show-overflow-tooltip />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reply" label="教师回复" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.reply || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="提交时间" width="170">
              <template #default="{ row }">
                {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

interface MyCourse {
  course_id: number
  course_name: string
  class_name: string
  schedules: { schedule_id: number; weekday: number; start_time: string; end_time: string; location: string | null }[]
}

interface LeaveRecord {
  id: number
  schedule_id: number
  leave_date: string
  reason: string
  status: string
  created_at: string | null
  course_name: string | null
  class_name: string | null
}

const courseOptions = ref<MyCourse[]>([])
const scheduleOptions = ref<MyCourse['schedules']>([])
const selectedCourseId = ref<number | null>(null)
const leaves = ref<LeaveRecord[]>([])
const loading = ref(false)
const submitting = ref(false)

const leaveForm = reactive({
  schedule_id: null as number | null,
  leave_date: '',
  reason: '',
})

const weekdayMap: Record<number, string> = { 1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 7: '周日' }
const weekdayText = (wd: number) => weekdayMap[wd] || `星期${wd}`

const statusText = (s: string) => ({ pending: '待审批', approved: '已通过', rejected: '已拒绝' }[s] || s)
const statusType = (s: string) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info') as 'warning' | 'success' | 'danger' | 'info'

const onCourseChange = () => {
  leaveForm.schedule_id = null
  leaveForm.leave_date = ''
  if (!selectedCourseId.value) {
    scheduleOptions.value = []
    return
  }
  const course = courseOptions.value.find(c => c.course_id === selectedCourseId.value)
  scheduleOptions.value = course?.schedules || []
}

/* ---------- 日期选择：只允许选排课对应的星期 ---------- */
const getSelectedWeekday = () => {
  if (!leaveForm.schedule_id) return null
  const s = scheduleOptions.value.find(s => s.schedule_id === leaveForm.schedule_id)
  return s?.weekday ?? null
}

const disabledDate = (date: Date) => {
  const weekday = getSelectedWeekday()
  if (weekday === null) return true
  // JS getDay(): 0=周日,1=周一,...,6=周六  →  后端 weekday: 1=周一,...,7=周日
  const jsDay = date.getDay()
  const backendDay = jsDay === 0 ? 7 : jsDay
  return backendDay !== weekday
}

const fetchCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses/my')
    courseOptions.value = res.data
  } catch { /* ignore */ }
}

const fetchLeaves = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/leave/my')
    leaves.value = res.data
  } catch {
    ElMessage.error('获取请假记录失败')
  } finally {
    loading.value = false
  }
}

const submitLeave = async () => {
  if (!leaveForm.schedule_id) return ElMessage.warning('请选择排课')
  if (!leaveForm.leave_date) return ElMessage.warning('请选择请假日期')
  if (!leaveForm.reason.trim()) return ElMessage.warning('请填写请假理由')

  submitting.value = true
  try {
    await request.post('/api/v1/leave', {
      schedule_id: leaveForm.schedule_id,
      leave_date: leaveForm.leave_date,
      reason: leaveForm.reason,
    })
    ElMessage.success('请假申请已提交')
    leaveForm.schedule_id = null
    leaveForm.leave_date = ''
    leaveForm.reason = ''
    selectedCourseId.value = null
    scheduleOptions.value = []
    fetchLeaves()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchCourses()
  fetchLeaves()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

<style>
/* 高亮可选的排课日期（非 scoped，因为 date-picker 弹出层在 body 下） */
.el-date-table td.available:not(.disabled):not(.is-disabled) .el-date-table-cell__text {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  width: 30px;
  height: 30px;
  background-color: #e1f3d8;
  color: #67c23a;
  font-weight: 600;
  border-radius: 50%;
}
</style>
