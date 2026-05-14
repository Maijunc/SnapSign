<template>
  <div class="my-courses-container">
    <!-- ===== 今日课程快捷区 ===== -->
    <el-card v-if="todaySchedules.length > 0" shadow="hover" style="margin-bottom: 20px;">
      <template #header>
        <div class="card-header">
          <span>🕐 今日课程</span>
          <el-tag type="info" size="small">{{ todayLabel }}</el-tag>
        </div>
      </template>
      <div class="today-cards">
        <el-card
          v-for="s in todaySchedules"
          :key="s.id"
          shadow="hover"
          class="today-card"
        >
          <div class="today-card-body">
            <div class="today-card-info">
              <div class="today-card-name">{{ s.course_name }}</div>
              <div class="today-card-detail">
                {{ s.class_name }} · {{ s.start_time }}~{{ s.end_time }} · {{ s.location || '无教室' }}
              </div>
            </div>
            <div class="today-card-actions">
              <el-button type="success" @click="goCheckIn(s)">开启打卡</el-button>
              <el-button type="primary" plain @click="viewAttendance(s)">考勤记录</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>

    <!-- ===== 全部排课总览 ===== -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📚 全部排课总览</span>
        </div>
      </template>

      <el-empty v-if="allSchedules.length === 0" description="暂无排课数据" />

      <el-table v-else :data="allSchedules" stripe style="width: 100%" :default-sort="{ prop: 'weekday', order: 'ascending' }">
        <el-table-column prop="course_name" label="课程" min-width="120">
          <template #default="{ row }">
            <el-tag type="primary" size="small">{{ row.course_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" width="130" />
        <el-table-column label="星期" width="80" prop="weekday" sortable>
          <template #default="{ row }">{{ weekdayText(row.weekday) }}</template>
        </el-table-column>
        <el-table-column label="时间" width="140">
          <template #default="{ row }">{{ row.start_time }} ~ {{ row.end_time }}</template>
        </el-table-column>
        <el-table-column prop="location" label="教室" width="130" />
        <el-table-column label="首次上课" width="120">
          <template #default="{ row }">{{ row.start_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="周数" width="70" align="center">
          <template #default="{ row }">{{ row.total_weeks ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="goCheckIn(row)">开启打卡</el-button>
            <el-button type="primary" size="small" plain @click="viewAttendance(row)">考勤记录</el-button>
            <el-button type="info" size="small" plain @click="viewWeeks(row)">周次详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 考勤记录弹窗 -->
    <el-dialog v-model="showAttendance" :title="'📋 考勤记录 — ' + attendanceTitle" width="700px">
      <el-empty v-if="attendanceRecords.length === 0" description="暂无签到记录" />
      <el-table v-else :data="attendanceRecords" stripe>
        <el-table-column prop="student_name" label="学生姓名" />
        <el-table-column label="签到时间">
          <template #default="{ row }">{{ formatTime(row.check_in_time) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'present' ? 'success' : row.status === 'late' ? 'warning' : 'danger'" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="匹配距离" width="120">
          <template #default="{ row }">{{ row.face_distance?.toFixed(3) ?? '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 周次详情弹窗 -->
    <el-dialog v-model="showWeeks" :title="`📅 周次详情 - ${weekScheduleTitle}`" width="500px">
      <el-table :data="weeksList" stripe border v-loading="weeksLoading">
        <el-table-column prop="week" label="周次" width="80" align="center">
          <template #default="{ row }">第{{ row.week }}周</template>
        </el-table-column>
        <el-table-column prop="date" label="上课日期" width="140" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag v-if="row.is_holiday" type="danger" size="small">🎉 {{ row.holiday_name }}</el-tag>
            <el-tag v-else type="success" size="small">正常上课</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const router = useRouter()

interface Schedule {
  id: number
  course_id: number
  class_id: number
  course_name: string
  class_name: string
  weekday: number
  start_date: string
  total_weeks: number
  start_time: string
  end_time: string
  location: string
}

const allSchedules = ref<Schedule[]>([])
const todaySchedules = ref<Schedule[]>([])

// 今日星期标签
const todayWeekday = new Date().getDay() || 7  // 1=Mon...7=Sun
const weekdayLabels = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
const todayLabel = weekdayLabels[todayWeekday]

// 加载全部排课
const fetchAllSchedules = async () => {
  try {
    const coursesRes = await request.get('/api/v1/courses')
    const courses = coursesRes.data
    const all: Schedule[] = []
    for (const course of courses) {
      const res = await request.get(`/api/v1/courses/${course.id}/schedules`)
      for (const s of res.data) {
        all.push({ ...s, course_name: s.course_name || course.name })
      }
    }
    allSchedules.value = all
    todaySchedules.value = all.filter(s => s.weekday === todayWeekday)
  } catch {
    ElMessage.error('获取排课数据失败')
  }
}

// 考勤记录弹窗
const showAttendance = ref(false)
const attendanceRecords = ref<any[]>([])
const attendanceTitle = ref('')

const viewAttendance = async (schedule: Schedule) => {
  attendanceTitle.value = `${schedule.course_name} - ${schedule.class_name}`
  try {
    const res = await request.get(`/api/v1/attendance/${schedule.id}`)
    attendanceRecords.value = res.data
    showAttendance.value = true
  } catch {
    ElMessage.error('获取考勤记录失败')
  }
}

// 周次详情弹窗
const showWeeks = ref(false)
const weeksList = ref<any[]>([])
const weeksLoading = ref(false)
const weekScheduleTitle = ref('')

const viewWeeks = async (schedule: Schedule) => {
  weekScheduleTitle.value = `${schedule.course_name} - ${schedule.class_name}`
  weeksLoading.value = true
  showWeeks.value = true
  try {
    const res = await request.get(`/api/v1/schedules/${schedule.id}/weeks`)
    weeksList.value = res.data
  } catch {
    ElMessage.error('获取周次详情失败')
  } finally {
    weeksLoading.value = false
  }
}

// 跳转打卡
const goCheckIn = (schedule: Schedule) => {
  router.push({
    path: '/check_in',
    query: { scheduleId: schedule.id, title: `${schedule.course_name} - ${schedule.class_name}` },
  })
}

// 工具函数
const weekdayText = (d: number) => weekdayLabels[d] || ''
const statusText = (s: string) => ({ present: '已到', late: '迟到', absent: '缺勤' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

onMounted(() => fetchAllSchedules())
</script>

<style scoped>
.my-courses-container { padding: 0; }
.card-header {
  font-weight: bold;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 今日课程卡片 */
.today-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.today-card {
  flex: 1;
  min-width: 300px;
  max-width: 500px;
}
.today-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.today-card-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.today-card-detail {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.today-card-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
</style>
