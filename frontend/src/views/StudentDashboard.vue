<template>
  <div class="student-dashboard">
    <!-- 今日课程 -->
    <el-card shadow="hover" style="margin-bottom: 20px;" v-loading="todayLoading">
      <template #header><span style="font-weight: bold;">📅 今日课程</span></template>
      <el-empty v-if="!todayLoading && todayCourses.length === 0" description="今天没有课程安排" :image-size="60" />
      <div v-else class="today-courses">
        <div v-for="ev in todayCourses" :key="ev.schedule_id" class="today-course-item">
          <div class="course-info">
            <span class="course-name">{{ ev.course_name }}</span>
            <el-tag size="small" type="info">{{ ev.class_name }}</el-tag>
          </div>
          <div class="course-detail">
            <span>🕐 {{ ev.start_time }} - {{ ev.end_time }}</span>
            <span v-if="ev.location">📍 {{ ev.location }}</span>
            <el-tag v-if="ev.is_holiday" type="danger" size="small">{{ ev.holiday_name || '节假日停课' }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #409eff;">{{ stats.total_records }}</div>
          <div class="stat-label">考勤总次数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #67c23a;">{{ stats.present_count }}</div>
          <div class="stat-label">正常签到</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #e6a23c;">{{ stats.late_count }}</div>
          <div class="stat-label">迟到次数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #f56c6c;">{{ stats.absent_count }}</div>
          <div class="stat-label">缺勤次数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 出勤率 -->
    <el-card shadow="hover" style="margin-bottom: 20px;" v-if="stats.attendance_rate !== null">
      <template #header><span style="font-weight: bold;">📊 我的总出勤率</span></template>
      <div class="attendance-rate">
        <span class="attendance-rate-label">当前总出勤率</span>
        <el-progress
          :percentage="stats.attendance_rate || 0"
          :stroke-width="20"
          :color="stats.attendance_rate >= 80 ? '#67c23a' : stats.attendance_rate >= 60 ? '#e6a23c' : '#f56c6c'"
          :format="(p: number) => p + '%'"
          class="attendance-rate-progress"
        />
      </div>
    </el-card>

    <!-- 各课程出勤统计 -->
    <el-card shadow="hover" v-loading="loading">
      <template #header><span style="font-weight: bold;">📚 各课程出勤情况</span></template>
      <el-empty v-if="!loading && stats.course_stats.length === 0" description="暂无考勤数据" />
      <el-table v-else :data="stats.course_stats" stripe border>
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="present" label="正常" width="80" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: bold;">{{ row.present }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="late" label="迟到" width="80" align="center">
          <template #default="{ row }">
            <span style="color: #e6a23c; font-weight: bold;">{{ row.late }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="absent" label="缺勤" width="80" align="center">
          <template #default="{ row }">
            <span style="color: #f56c6c; font-weight: bold;">{{ row.absent }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="总次数" width="80" align="center" />
        <el-table-column label="出勤率" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.rate >= 80 ? 'success' : row.rate >= 60 ? 'warning' : 'danger'" size="small">
              {{ row.rate }}%
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const loading = ref(false)
const todayLoading = ref(false)
const todayCourses = ref<any[]>([])
const stats = reactive({
  total_records: 0,
  present_count: 0,
  late_count: 0,
  absent_count: 0,
  attendance_rate: null as number | null,
  course_stats: [] as any[],
})

const fetchStats = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/dashboard/student_stats')
    Object.assign(stats, res.data)
  } catch {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

const fetchTodayCourses = async () => {
  todayLoading.value = true
  try {
    const now = new Date()
    const res = await request.get('/api/v1/calendar', {
      params: { year: now.getFullYear(), month: now.getMonth() + 1 },
    })
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    const todayData = (res.data as any[]).find((d: any) => d.date === todayStr)
    todayCourses.value = todayData?.events || []
  } catch { /* ignore */ }
  finally { todayLoading.value = false }
}

onMounted(() => {
  fetchStats()
  fetchTodayCourses()
})
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 10px 0;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}
.stat-label {
  font-size: 14px;
  color: #909399;
}
.today-courses {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.today-course-item {
  padding: 12px 16px;
  border-radius: 8px;
  background: #f5f7fa;
  border-left: 4px solid #409eff;
}
.course-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.course-name {
  font-weight: 600;
  font-size: 15px;
}
.course-detail {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #606266;
}

.attendance-rate {
  display: flex;
  align-items: center;
  gap: 20px;
}

.attendance-rate-label {
  font-size: 15px;
  font-weight: 600;
  color: #606266;
  white-space: nowrap;
}

.attendance-rate-progress {
  flex: 1;
}

@media (max-width: 768px) {
  .attendance-rate {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
}
</style>
