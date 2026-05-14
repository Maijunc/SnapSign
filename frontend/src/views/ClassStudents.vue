<template>
  <div class="class-students-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>👥 班级学生名册</span>
          <div class="filter-area">
            <el-select v-model="selectedCourseId" placeholder="选择课程" clearable style="width: 220px;" @change="onCourseChange">
              <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="selectedClassId" placeholder="选择班级" clearable style="width: 180px;" :disabled="classList.length === 0" @change="fetchStudents">
              <el-option v-for="cl in classList" :key="cl.id" :label="cl.name" :value="cl.id" />
            </el-select>
          </div>
        </div>
      </template>

      <el-empty v-if="!selectedClassId" description="请先选择课程和班级" :image-size="80" />

      <template v-else>
        <div class="stats-bar">
          <el-tag type="primary">{{ selectedCourseName }}</el-tag>
          <el-tag type="info">{{ selectedClassName }}</el-tag>
          <el-tag type="success">共 {{ students.length }} 人</el-tag>
        </div>

        <el-table :data="students" v-loading="loading" stripe border style="width: 100%">
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="student_id" label="学号" width="180" align="center" />
          <el-table-column prop="name" label="姓名" min-width="150" align="center">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="人脸特征" width="140" align="center">
            <template #default>
              <el-tag type="success" size="small">已录入</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

interface CourseItem { id: number; name: string; classes: { id: number; name: string }[] }
interface StudentItem { id: number; student_id: string; name: string | null }

const courses = ref<CourseItem[]>([])
const classList = ref<{ id: number; name: string }[]>([])
const students = ref<StudentItem[]>([])
const selectedCourseId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const loading = ref(false)

const selectedCourseName = ref('')
const selectedClassName = ref('')

const fetchCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses')
    courses.value = res.data
  } catch { /* ignore */ }
}

const onCourseChange = () => {
  selectedClassId.value = null
  students.value = []
  if (!selectedCourseId.value) {
    classList.value = []
    selectedCourseName.value = ''
    return
  }
  const course = courses.value.find(c => c.id === selectedCourseId.value)
  classList.value = course?.classes || []
  selectedCourseName.value = course?.name || ''
  selectedClassName.value = ''
  // 如果只有一个班级，自动选中
  if (classList.value.length === 1) {
    selectedClassId.value = classList.value[0].id
    fetchStudents()
  }
}

const fetchStudents = async () => {
  if (!selectedClassId.value) {
    students.value = []
    return
  }
  selectedClassName.value = classList.value.find(c => c.id === selectedClassId.value)?.name || ''
  loading.value = true
  try {
    const res = await request.get(`/api/v1/classes/${selectedClassId.value}/students`)
    students.value = res.data
  } catch {
    ElMessage.error('获取学生列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.filter-area {
  display: flex;
  gap: 10px;
}
.stats-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
</style>
