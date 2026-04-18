<template>
  <div class="dashboard-container">
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

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card shadow="hover" header="近 7 日出勤趋势">
          <div ref="chartRef" style="height: 350px; width: 100%;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span>实时考勤动态</span>
              <el-select v-model="selectedScheduleId" placeholder="选择排课" size="small" style="width: 220px;" @change="fetchRecent">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from 'vue'
import { User, Check, Warning, Close } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '../utils/request'

// --- 统计卡片 ---
const statCards = ref([
  { title: '加载中...', value: 0, icon: shallowRef(User), color: '#409EFF' },
  { title: '今日已签到', value: 0, icon: shallowRef(Check), color: '#67C23A' },
  { title: '今日迟到', value: 0, icon: shallowRef(Warning), color: '#E6A23C' },
  { title: '今日缺勤', value: 0, icon: shallowRef(Close), color: '#F56C6C' },
])

const fetchStats = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/stats')
    const d = res.data
    statCards.value[0].title = d.card1_title
    statCards.value[0].value = d.card1_value
    statCards.value[1].title = d.card2_title
    statCards.value[1].value = d.card2_value
    statCards.value[2].title = d.card3_title
    statCards.value[2].value = d.card3_value
    statCards.value[3].title = d.card4_title
    statCards.value[3].value = d.card4_value
  } catch { /* 静默 */ }
}

// --- 趋势图 ---
const chartRef = ref<HTMLDivElement | null>(null)
let myChart: echarts.ECharts | null = null

const fetchTrend = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/trend')
    const dates = res.data.map((i: any) => i.date)
    const rates = res.data.map((i: any) => i.rate)
    if (myChart) {
      myChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: dates },
        yAxis: { type: 'value', name: '出勤率(%)', min: 0, max: 100 },
        series: [{
          data: rates,
          type: 'line',
          smooth: true,
          areaStyle: { color: 'rgba(64,158,255,0.2)' },
          itemStyle: { color: '#409EFF' },
        }],
      })
    }
  } catch { /* 静默 */ }
}

// --- 今日排课下拉 ---
const schedulesToday = ref<any[]>([])
const selectedScheduleId = ref<number | null>(null)

const fetchSchedulesToday = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/schedules_today')
    schedulesToday.value = res.data
    if (res.data.length > 0) {
      selectedScheduleId.value = res.data[0].id
      fetchRecent()
    }
  } catch { /* 静默 */ }
}

// --- 实时考勤 ---
const recentActivities = ref<any[]>([])

const fetchRecent = async () => {
  if (!selectedScheduleId.value) return
  try {
    const res = await request.get('/api/v1/dashboard/recent', { params: { schedule_id: selectedScheduleId.value } })
    recentActivities.value = res.data
  } catch { /* 静默 */ }
}

const statusText = (s: string) => ({ present: '签到成功', late: '迟到', absent: '缺勤' }[s] || s)

onMounted(async () => {
  if (chartRef.value) {
    myChart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => myChart?.resize())
  }
  await Promise.all([fetchStats(), fetchTrend(), fetchSchedulesToday()])
})
</script>

<style scoped>
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
</style>