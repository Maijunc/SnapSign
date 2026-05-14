<template>
  <div class="student-courses">
    <el-card shadow="hover" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>📚 我的课程</span>
          <el-button type="primary" icon="Refresh" @click="fetchCourses" size="small" :loading="loading">刷新</el-button>
        </div>
      </template>

      <el-empty v-if="!loading && courses.length === 0" description="暂无课程信息，请联系管理员分配班级" />

      <el-table v-else :data="courses" stripe border style="width: 100%">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="teacher_name" label="授课教师" width="120" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column label="上课时间" min-width="200">
          <template #default="{ row }">
            <div v-for="s in row.schedules" :key="s.schedule_id" class="schedule-line">
              <el-tag size="small" type="info" style="margin-right: 6px;">{{ weekdayText(s.weekday) }}</el-tag>
              {{ s.start_time }} - {{ s.end_time }}
            </div>
            <span v-if="row.schedules.length === 0" style="color: #909399;">未排课</span>
          </template>
        </el-table-column>
        <el-table-column label="上课地点" width="150">
          <template #default="{ row }">
            <div v-for="s in row.schedules" :key="s.schedule_id" class="schedule-line">
              {{ s.location || '未指定' }}
            </div>
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

interface Schedule {
  schedule_id: number
  weekday: number
  start_time: string
  end_time: string
  location: string | null
}

interface MyCourse {
  course_id: number
  course_name: string
  teacher_name: string | null
  class_name: string
  schedules: Schedule[]
}

const courses = ref<MyCourse[]>([])
const loading = ref(false)

const weekdayMap: Record<number, string> = {
  1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 7: '周日',
}
const weekdayText = (wd: number) => weekdayMap[wd] || `星期${wd}`

const fetchCourses = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/courses/my')
    courses.value = res.data
  } catch {
    ElMessage.error('获取课程信息失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => fetchCourses())
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
.schedule-line {
  line-height: 2;
}
</style>
