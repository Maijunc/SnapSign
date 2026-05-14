<template>
  <div class="dashboard-container">
    <!-- ===== 第一行：统计卡片 ===== -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6" v-for="(stat, index) in statCards" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" :style="{ color: stat.color }"><component :is="stat.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-title">{{ stat.title }}</div>
              <div class="stat-value">{{ stat.value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 出勤率横条（仅教师可见） -->
    <div v-if="attendanceRate !== null" class="rate-bar" style="margin-top: 12px;">
      <el-card shadow="hover">
        <div class="rate-content">
          <span class="rate-label">{{ selectedScheduleId ? '当前课次出勤率' : '今日总出勤率' }}</span>
          <el-progress
            :percentage="attendanceRate"
            :stroke-width="20"
            :color="rateColor(attendanceRate)"
            :format="(p: number) => p + '%'"
            style="flex: 1; margin: 0 20px;"
          />
        </div>
      </el-card>
    </div>

    <!-- ===== 第二行：各课出勤概览(左) + 实时考勤(右) ===== -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <span>📊 今日各课出勤概览</span>
          </template>
          <el-empty v-if="courseAttendance.length === 0" description="今日暂无排课" :image-size="60" />
          <el-table v-else :data="courseAttendance" stripe style="width: 100%" show-summary :summary-method="summaryMethod">
            <el-table-column prop="course_name" label="课程" min-width="120" />
            <el-table-column prop="class_name" label="班级" width="130" />
            <el-table-column prop="time_range" label="时间" width="120" />
            <el-table-column prop="expected" label="应到" width="70" align="center" />
            <el-table-column label="已到" width="70" align="center">
              <template #default="{ row }">{{ row.present + row.late }}</template>
            </el-table-column>
            <el-table-column prop="late" label="迟到" width="70" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.late > 0 ? '#E6A23C' : '' }">{{ row.late }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="absent" label="缺勤" width="70" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.absent > 0 ? '#F56C6C' : '' }">{{ row.absent }}</span>
              </template>
            </el-table-column>
            <el-table-column label="出勤率" width="180" align="center">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.rate"
                  :stroke-width="14"
                  :color="rateColor(row.rate)"
                  :format="(p: number) => p + '%'"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="goCheckIn(row)">打卡</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span>实时考勤动态</span>
              <el-select v-model="selectedScheduleId" placeholder="选择排课" size="small" style="width: 220px;" @change="onScheduleChange">
                <el-option v-for="s in schedulesToday" :key="s.id" :label="s.label" :value="s.id" />
              </el-select>
            </div>
          </template>
          <el-empty v-if="recentActivities.length === 0" description="暂无签到记录" :image-size="60" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="(activity, index) in recentActivities"
              :key="index"
              :type="activity.status === 'present' ? 'success' : activity.status === 'late' ? 'warning' : 'danger'"
              :timestamp="activity.check_in_time || ''"
            >
              {{ activity.student_name }} - {{ statusText(activity.status) }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 第三行：出勤趋势（全宽 + 课程筛选） ===== -->
    <el-row style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span>📈 近 7 日出勤趋势</span>
              <el-select v-model="trendCourseId" placeholder="全部课程" size="small" clearable style="width: 200px;" @change="fetchTrend">
                <el-option v-for="c in myCourses" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </div>
          </template>
          <div ref="chartRef" style="height: 300px; width: 100%;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { User, Check, Warning, Close } from '@element-plus/icons-vue'
import type { TableColumnCtx } from 'element-plus'
import * as echarts from 'echarts'
import request from '../utils/request'

const router = useRouter()

// ======================== 统计卡片 ========================
const statCards = ref([
  { title: '加载中...', value: 0, icon: shallowRef(User), color: '#409EFF' },
  { title: '今日已签到', value: 0, icon: shallowRef(Check), color: '#67C23A' },
  { title: '今日迟到', value: 0, icon: shallowRef(Warning), color: '#E6A23C' },
  { title: '今日缺勤', value: 0, icon: shallowRef(Close), color: '#F56C6C' },
])
const attendanceRate = ref<number | null>(null)

const fetchStats = async () => {
  try {
    const params: any = {}
    if (selectedScheduleId.value) params.schedule_id = selectedScheduleId.value
    const res = await request.get('/api/v1/dashboard/stats', { params })
    const d = res.data
    statCards.value[0].title = d.card1_title
    statCards.value[0].value = d.card1_value
    statCards.value[1].title = d.card2_title
    statCards.value[1].value = d.card2_value
    statCards.value[2].title = d.card3_title
    statCards.value[2].value = d.card3_value
    statCards.value[3].title = d.card4_title
    statCards.value[3].value = d.card4_value
    attendanceRate.value = d.attendance_rate ?? null
  } catch { /* 静默 */ }
}

// ======================== 出勤率颜色 ========================
const rateColor = (rate: number) => {
  if (rate >= 90) return '#67C23A'
  if (rate >= 70) return '#E6A23C'
  return '#F56C6C'
}

// ======================== 各课出勤概览 ========================
interface CourseAtt {
  schedule_id: number
  course_name: string
  class_name: string
  time_range: string
  expected: number
  present: number
  late: number
  absent: number
  rate: number
}
const courseAttendance = ref<CourseAtt[]>([])

const fetchCourseAttendance = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/course_attendance')
    courseAttendance.value = res.data
  } catch { /* 静默 */ }
}

const goCheckIn = (row: CourseAtt) => {
  router.push({
    path: '/check_in',
    query: { scheduleId: row.schedule_id, title: `${row.course_name} - ${row.class_name}` },
  })
}

// 汇总行
const summaryMethod = ({ columns, data }: { columns: TableColumnCtx<CourseAtt>[]; data: CourseAtt[] }) => {
  return columns.map((_col, index) => {
    if (index === 0) return '合计'
    if (index === 1 || index === 2) return ''
    if (index === 3) return data.reduce((s, r) => s + r.expected, 0)
    if (index === 4) return data.reduce((s, r) => s + r.present + r.late, 0)
    if (index === 5) return data.reduce((s, r) => s + r.late, 0)
    if (index === 6) return data.reduce((s, r) => s + r.absent, 0)
    if (index === 7) {
      const totalExpected = data.reduce((s, r) => s + r.expected, 0)
      const totalSigned = data.reduce((s, r) => s + r.present + r.late, 0)
      return totalExpected > 0 ? (totalSigned / totalExpected * 100).toFixed(1) + '%' : '-'
    }
    return ''
  })
}

// ======================== 趋势图 ========================
const chartRef = ref<HTMLDivElement | null>(null)
let myChart: echarts.ECharts | null = null

// 课程列表（用于筛选下拉）
interface CourseItem { id: number; name: string }
const myCourses = ref<CourseItem[]>([])
const trendCourseId = ref<number | undefined>(undefined)

const fetchMyCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses')
    myCourses.value = res.data.map((c: any) => ({ id: c.id, name: c.name }))
  } catch { /* 静默 */ }
}

const fetchTrend = async () => {
  try {
    const params: any = {}
    if (trendCourseId.value) params.course_id = trendCourseId.value
    const res = await request.get('/api/v1/dashboard/trend', { params })
    const dates = res.data.map((i: any) => i.date)
    const rates = res.data.map((i: any) => i.rate)
    if (myChart) {
      myChart.setOption({
        tooltip: { trigger: 'axis', formatter: '{b}<br/>出勤率: {c}%' },
        grid: { left: 50, right: 30, top: 30, bottom: 30 },
        xAxis: { type: 'category', data: dates },
        yAxis: { type: 'value', name: '出勤率(%)', min: 0, max: 100 },
        series: [{
          data: rates,
          type: 'line',
          smooth: true,
          areaStyle: { color: 'rgba(64,158,255,0.15)' },
          itemStyle: { color: '#409EFF' },
          lineStyle: { width: 3 },
          symbolSize: 8,
        }],
      })
    }
  } catch { /* 静默 */ }
}

// ======================== 今日排课下拉 ========================
const schedulesToday = ref<any[]>([])
const selectedScheduleId = ref<number | null>(null)

const onScheduleChange = async () => {
  await Promise.all([fetchStats(), fetchRecent()])
}

const fetchSchedulesToday = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/schedules_today')
    schedulesToday.value = res.data
    if (res.data.length > 0) {
      selectedScheduleId.value = res.data[0].id
      await onScheduleChange()
    } else {
      selectedScheduleId.value = null
      await fetchStats()
    }
  } catch { /* 静默 */ }
}

// ======================== 实时考勤 ========================
const recentActivities = ref<any[]>([])

const fetchRecent = async () => {
  if (!selectedScheduleId.value) return
  try {
    const res = await request.get('/api/v1/dashboard/recent', { params: { schedule_id: selectedScheduleId.value } })
    recentActivities.value = res.data
  } catch { /* 静默 */ }
}

const statusText = (s: string) => ({ present: '签到成功', late: '迟到', absent: '缺勤' }[s] || s)

// ======================== 初始化 ========================
onMounted(async () => {
  if (chartRef.value) {
    myChart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => myChart?.resize())
  }
  await Promise.all([
    fetchCourseAttendance(),
    fetchTrend(),
    fetchSchedulesToday(),
    fetchMyCourses(),
  ])
})
</script>

<style scoped>
.dashboard-container {
  padding: 10px;
}

.stat-content {
  display: flex;
  align-items: center;
}
.stat-icon {
  font-size: 48px;
  margin-right: 20px;
}
.stat-info {
  display: flex;
  flex-direction: column;
}
.stat-title {
  font-size: 14px;
  color: #909399;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-top: 5px;
}

.rate-content {
  display: flex;
  align-items: center;
}
.rate-label {
  font-size: 15px;
  font-weight: 600;
  color: #606266;
  white-space: nowrap;
}
</style>