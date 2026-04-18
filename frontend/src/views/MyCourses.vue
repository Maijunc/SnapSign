<template>
  <div class="my-courses-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📚 我的课程</span>
        </div>
      </template>

      <el-empty v-if="courses.length === 0" description="暂无课程数据" />

      <el-collapse v-else v-model="activeCourse" accordion>
        <el-collapse-item
          v-for="course in courses"
          :key="course.id"
          :name="course.id"
        >
          <template #title>
            <div class="course-title">
              <el-tag type="primary" size="small">{{ course.name }}</el-tag>
              <span class="course-classes">
                {{ course.classes.map((c: any) => c.name).join('、') || '未分配班级' }}
              </span>
            </div>
          </template>

          <!-- 排课列表 -->
          <div v-loading="loadingSchedules[course.id]">
            <el-empty v-if="scheduleMap[course.id]?.length === 0" description="该课程暂无排课" :image-size="60" />

            <el-table v-else :data="scheduleMap[course.id] || []" stripe style="width: 100%">
              <el-table-column label="星期" width="100">
                <template #default="{ row }">{{ weekdayText(row.weekday) }}</template>
              </el-table-column>
              <el-table-column label="首次上课" width="130">
                <template #default="{ row }">{{ row.start_date || '-' }}</template>
              </el-table-column>
              <el-table-column label="周数" width="70" align="center">
                <template #default="{ row }">{{ row.total_weeks ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="时间" width="180">
                <template #default="{ row }">{{ row.start_time }} ~ {{ row.end_time }}</template>
              </el-table-column>
              <el-table-column prop="class_name" label="班级" width="150" />
              <el-table-column prop="location" label="教室" />
              <el-table-column label="操作" width="280">
                <template #default="{ row }">
                  <el-button type="primary" size="small" @click="viewWeeks(row)">
                    周次详情
                  </el-button>
                  <el-button type="success" size="small" @click="goCheckIn(row)">
                    开启打卡
                  </el-button>
                  <el-button type="info" size="small" @click="viewAttendance(row)">
                    考勤记录
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 考勤记录弹窗 -->
    <el-dialog v-model="showAttendance" title="📋 考勤记录" width="700px">
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
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const router = useRouter()

// 课程列表
const courses = ref<any[]>([])
const activeCourse = ref<number | null>(null)

// 排课 map：{ courseId: schedules[] }
const scheduleMap = reactive<Record<number, any[]>>({})
const loadingSchedules = reactive<Record<number, boolean>>({})

// 考勤弹窗
const showAttendance = ref(false)
const attendanceRecords = ref<any[]>([])

// 周次弹窗
const showWeeks = ref(false)
const weeksList = ref<any[]>([])
const weeksLoading = ref(false)
const weekScheduleTitle = ref('')

// 加载课程列表
const fetchCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses')
    courses.value = res.data
  } catch {
    ElMessage.error('获取课程列表失败')
  }
}

// 当展开某个课程时，加载其排课
watch(activeCourse, async (courseId) => {
  if (courseId == null || scheduleMap[courseId]) return
  loadingSchedules[courseId] = true
  try {
    const res = await request.get(`/api/v1/courses/${courseId}/schedules`)
    scheduleMap[courseId] = res.data
  } catch {
    ElMessage.error('获取排课失败')
  } finally {
    loadingSchedules[courseId] = false
  }
})

// 查看周次详情
const viewWeeks = async (schedule: any) => {
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

// 跳转打卡页
const goCheckIn = (schedule: any) => {
  router.push({ path: '/check_in', query: { scheduleId: schedule.id, title: `${schedule.course_name} - ${schedule.class_name}` } })
}

// 查看考勤记录
const viewAttendance = async (schedule: any) => {
  try {
    const res = await request.get(`/api/v1/attendance/${schedule.id}`)
    attendanceRecords.value = res.data
    showAttendance.value = true
  } catch {
    ElMessage.error('获取考勤记录失败')
  }
}

// 工具函数
const weekdayText = (d: number) => ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][d] || ''
const statusText = (s: string) => ({ present: '已到', late: '迟到', absent: '缺勤' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

fetchCourses()
</script>

<style scoped>
.my-courses-container { padding: 0; }
.card-header { font-weight: bold; font-size: 16px; }
.course-title { display: flex; align-items: center; gap: 12px; }
.course-classes { color: #909399; font-size: 13px; }
</style>
