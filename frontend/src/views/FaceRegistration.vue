<template>
  <div class="face-reg-container">
    <el-row :gutter="20">
      <!-- 左侧：班级学生列表 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>👥 班级学生名册</span>
              <el-tag v-if="students.length > 0" type="success" size="small">
                {{ registeredCount }}/{{ students.length }} 已录入
              </el-tag>
            </div>
          </template>

          <!-- 筛选 -->
          <div class="filter-area">
            <el-select v-model="selectedCourseId" placeholder="选择课程" clearable style="width: 180px;" @change="onCourseChange" size="default">
              <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="selectedClassId" placeholder="选择班级" clearable style="width: 150px;" :disabled="classList.length === 0" @change="fetchStudents" size="default">
              <el-option v-for="cl in classList" :key="cl.id" :label="cl.name" :value="cl.id" />
            </el-select>
          </div>

          <!-- 学生列表 -->
          <el-empty v-if="!selectedClassId" description="请先选择课程和班级" :image-size="60" />

          <div v-else class="student-list" v-loading="listLoading">
            <div
              v-for="s in students"
              :key="s.id"
              :class="['student-item', { active: selectedStudent?.id === s.id, registered: s.has_face }]"
              @click="selectStudent(s)"
            >
              <div class="student-info">
                <span class="student-name">{{ s.name }}</span>
                <span class="student-id">{{ s.student_id }}</span>
              </div>
              <el-tag :type="s.has_face ? 'success' : 'danger'" size="small">
                {{ s.has_face ? '已录入' : '未录入' }}
              </el-tag>
            </div>
            <el-empty v-if="students.length === 0" description="该班级暂无学生" :image-size="40" />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：摄像头采集区 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>📷 人脸特征采集</span>
              <div v-if="selectedStudent" class="selected-info">
                <el-tag type="primary">{{ selectedStudent.name }}</el-tag>
                <el-tag type="info">{{ selectedStudent.student_id }}</el-tag>
              </div>
            </div>
          </template>

          <!-- 未选学生 -->
          <el-empty v-if="!selectedStudent" description="请从左侧名册中选择一名学生" :image-size="80" />

          <!-- 采集区 -->
          <template v-else>
            <div class="camera-box" v-loading="isCameraStarting" element-loading-text="正在唤醒摄像头...">
              <div class="video-wrapper">
                <video ref="videoRef" autoplay playsinline class="video-stream"></video>
                <!-- 人脸引导框 -->
                <div v-if="isCameraReady" class="face-guide-overlay">
                  <svg viewBox="0 0 640 480" class="face-guide-svg">
                    <defs>
                      <mask id="faceMask">
                        <rect width="640" height="480" fill="white" />
                        <ellipse cx="320" cy="220" rx="130" ry="170" fill="black" />
                      </mask>
                    </defs>
                    <rect width="640" height="480" fill="rgba(0,0,0,0.35)" mask="url(#faceMask)" />
                    <ellipse cx="320" cy="220" rx="130" ry="170" fill="none" stroke="#67c23a" stroke-width="2" stroke-dasharray="8,4" />
                  </svg>
                </div>
              </div>
              <canvas ref="canvasRef" style="display: none;"></canvas>

              <div class="capture-tips" v-if="isCameraReady">
                <el-tag type="info" size="small">请让学生面部对准椭圆框</el-tag>
                <el-tag type="info" size="small">确保光线充足、无遮挡</el-tag>
              </div>

              <div class="camera-controls">
                <el-button type="primary" @click="startCamera" :disabled="isCameraReady">启动摄像头</el-button>
                <el-button type="success" size="large" @click="captureAndSubmit" :disabled="!isCameraReady" :loading="isSubmitting" icon="Check">
                  抓拍并录入
                </el-button>
                <el-button type="danger" @click="stopCamera" :disabled="!isCameraReady">关闭</el-button>
              </div>
            </div>

            <!-- 抓拍预览 -->
            <div class="preview-box" v-if="capturedImage">
              <p class="preview-title">最近抓拍：</p>
              <img :src="capturedImage" class="preview-img" />
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

interface CourseItem { id: number; name: string; classes: { id: number; name: string }[] }
interface StudentItem { id: number; student_id: string; name: string | null; has_face: boolean }

// ---- 班级筛选 ----
const courses = ref<CourseItem[]>([])
const classList = ref<{ id: number; name: string }[]>([])
const students = ref<StudentItem[]>([])
const selectedCourseId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const selectedStudent = ref<StudentItem | null>(null)
const listLoading = ref(false)

const registeredCount = computed(() => students.value.filter(s => s.has_face).length)

const fetchCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses')
    courses.value = res.data
  } catch { /* ignore */ }
}

const onCourseChange = () => {
  selectedClassId.value = null
  selectedStudent.value = null
  students.value = []
  if (!selectedCourseId.value) { classList.value = []; return }
  const course = courses.value.find(c => c.id === selectedCourseId.value)
  classList.value = course?.classes || []
  if (classList.value.length === 1) {
    selectedClassId.value = classList.value[0].id
    fetchStudents()
  }
}

const fetchStudents = async () => {
  selectedStudent.value = null
  if (!selectedClassId.value) { students.value = []; return }
  listLoading.value = true
  try {
    const res = await request.get(`/api/v1/classes/${selectedClassId.value}/students`)
    students.value = res.data
  } catch {
    ElMessage.error('获取学生列表失败')
  } finally {
    listLoading.value = false
  }
}

const selectStudent = (s: StudentItem) => {
  selectedStudent.value = s
  capturedImage.value = null
}

// ---- 摄像头 ----
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isCameraStarting = ref(false)
const isCameraReady = ref(false)
const isSubmitting = ref(false)
const capturedImage = ref<string | null>(null)
let mediaStream: MediaStream | null = null

const startCamera = async () => {
  isCameraStarting.value = true
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      isCameraReady.value = true
    }
  } catch {
    ElMessage.error('无法访问摄像头，请检查浏览器权限！')
  } finally {
    isCameraStarting.value = false
  }
}

const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    if (videoRef.value) videoRef.value.srcObject = null
    isCameraReady.value = false
    mediaStream = null
  }
}

// ---- 抓拍并注册 ----
const captureAndSubmit = async () => {
  if (!selectedStudent.value) return
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height)
  capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)

  isSubmitting.value = true
  try {
    const res = await request.post('/api/v1/faces/register', {
      student_id: selectedStudent.value.student_id,
      name: selectedStudent.value.name,
      image_base64: capturedImage.value,
    })
    if (res.data.status === 'success') {
      ElMessage.success(`${selectedStudent.value.name} 录入成功！`)
      // 更新列表中的状态
      const idx = students.value.findIndex(s => s.id === selectedStudent.value!.id)
      if (idx >= 0) students.value[idx].has_face = true
      // 自动跳到下一个未录入的学生
      autoSelectNext()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '录入失败')
  } finally {
    isSubmitting.value = false
  }
}

/** 录入成功后自动选中下一个未录入的学生 */
const autoSelectNext = () => {
  const currentIdx = students.value.findIndex(s => s.id === selectedStudent.value?.id)
  // 先向后找
  for (let i = currentIdx + 1; i < students.value.length; i++) {
    if (!students.value[i].has_face) {
      selectedStudent.value = students.value[i]
      capturedImage.value = null
      return
    }
  }
  // 再从头找
  for (let i = 0; i < currentIdx; i++) {
    if (!students.value[i].has_face) {
      selectedStudent.value = students.value[i]
      capturedImage.value = null
      return
    }
  }
  // 全部录完
  ElMessage.success('🎉 该班级所有学生均已完成人脸录入！')
}

onMounted(() => fetchCourses())
onBeforeUnmount(() => stopCamera())
</script>

<style scoped>
.face-reg-container { padding: 0; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.selected-info { display: flex; gap: 6px; }
.filter-area {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

/* 学生列表 */
.student-list {
  max-height: 520px;
  overflow-y: auto;
}
.student-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  border: 1px solid transparent;
}
.student-item:hover { background: #f5f7fa; }
.student-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}
.student-item.registered { opacity: 0.7; }
.student-item.registered.active { opacity: 1; }
.student-info { display: flex; flex-direction: column; gap: 2px; }
.student-name { font-weight: 600; font-size: 14px; color: #303133; }
.student-id { font-size: 12px; color: #909399; }

/* 摄像头 */
.camera-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  background-color: #000;
  border-radius: 8px;
  padding: 10px;
}
.video-wrapper { position: relative; width: 100%; max-width: 640px; }
.video-stream {
  width: 100%;
  border-radius: 4px;
  background-color: #2c3e50;
  aspect-ratio: 4/3;
  display: block;
}
.face-guide-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}
.face-guide-svg { width: 100%; height: 100%; }
.capture-tips {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
.camera-controls { margin-top: 12px; display: flex; gap: 10px; }
.preview-box {
  margin-top: 16px;
  text-align: center;
  border: 1px dashed #d9d9d9;
  padding: 10px;
  border-radius: 6px;
}
.preview-title { color: #606266; font-size: 14px; margin-bottom: 8px; }
.preview-img { max-width: 100%; max-height: 200px; border-radius: 4px; }
</style>