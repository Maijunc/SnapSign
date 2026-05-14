<template>
  <div class="attendance-container">
    <el-card shadow="hover" class="box-card">
      <template #header>
        <div class="check-header">
          <span>🕒 课堂自动打卡机</span>
          <div class="schedule-selector">
            <el-select
              v-model="currentScheduleId"
              placeholder="选择排课"
              size="default"
              style="width: 300px;"
              @change="onScheduleChange"
            >
              <el-option
                v-for="s in schedulesToday"
                :key="s.id"
                :label="s.label"
                :value="s.id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <!-- 未选排课时的提示 -->
      <el-empty v-if="!currentScheduleId" description="请先选择一节今日课程后开始打卡" :image-size="80">
        <template v-if="schedulesToday.length === 0">
          <p style="color: #909399; font-size: 13px;">今日暂无排课</p>
        </template>
      </el-empty>

      <!-- 正常打卡界面 -->
      <template v-else>
        <div class="course-info-bar">
          <el-tag type="primary" size="large">{{ courseTitle }}</el-tag>
        </div>

        <div class="camera-box" v-loading="isChecking" element-loading-text="正在进行生物特征比对...">
          <video ref="videoRef" autoplay playsinline class="video-stream"></video>
          <canvas ref="canvasRef" style="display: none;"></canvas>
        </div>

        <div class="controls">
          <el-button type="primary" size="large" @click="startCamera" :disabled="isCameraReady">
            1. 开启打卡机
          </el-button>
          <el-button type="success" size="large" @click="checkIn" :disabled="!isCameraReady" icon="Check">
            2. 点击签到
          </el-button>
        </div>

        <div v-if="resultMessage" :class="['result-box', resultStatus]">
          <h2>{{ resultMessage }}</h2>
          <p v-if="matchDistance">算法差异度: {{ matchDistance.toFixed(3) }} (阈值 &lt; 0.45)</p>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const route = useRoute()

// 今日排课列表
interface ScheduleOption { id: number; label: string }
const schedulesToday = ref<ScheduleOption[]>([])

// 当前选中的排课
const currentScheduleId = ref<number | null>(null)
const courseTitle = ref('')

// 如果 URL 带了 scheduleId，优先使用
const urlScheduleId = computed(() => Number(route.query.scheduleId) || null)
const urlTitle = computed(() => (route.query.title as string) || '')

const fetchSchedulesToday = async () => {
  try {
    const res = await request.get('/api/v1/dashboard/schedules_today')
    schedulesToday.value = (res.data as Array<{ id: number | string; label: string }>).map(item => ({
      id: Number(item.id),
      label: item.label,
    }))
  } catch { /* 静默 */ }
}

const ensureRouteScheduleOption = () => {
  if (!urlScheduleId.value) return
  const exists = schedulesToday.value.some(s => Number(s.id) === urlScheduleId.value)
  if (!exists) {
    schedulesToday.value.unshift({
      id: urlScheduleId.value,
      label: urlTitle.value || `排课 #${urlScheduleId.value}`,
    })
  }
}

const onScheduleChange = (id: number | string) => {
  const normalizedId = Number(id)
  currentScheduleId.value = normalizedId
  const found = schedulesToday.value.find(s => s.id === normalizedId)
  courseTitle.value = found?.label || ''
  // 切换排课时重置状态
  resultMessage.value = ''
  resultStatus.value = ''
  matchDistance.value = null
}

// 摄像头与签到
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isCameraReady = ref(false)
const isChecking = ref(false)
const resultMessage = ref('')
const resultStatus = ref('')
const matchDistance = ref<number | null>(null)

let mediaStream: MediaStream | null = null

const startCamera = async () => {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      isCameraReady.value = true
    }
  } catch {
    ElMessage.error('无法唤醒摄像头！')
  }
}

const checkIn = async () => {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d')?.drawImage(video, 0, 0)
  const base64Image = canvas.toDataURL('image/jpeg', 0.9)

  isChecking.value = true
  resultMessage.value = ''

  try {
    const res = await request.post('/api/v1/faces/check_in', {
      image_base64: base64Image,
      schedule_id: currentScheduleId.value,
    })

    if (res.data.status === 'success') {
      resultStatus.value = 'success'
      resultMessage.value = res.data.message
      matchDistance.value = res.data.distance
      ElMessage.success('✅ 签到成功！')
    } else if (res.data.status === 'duplicate') {
      resultStatus.value = 'success'
      resultMessage.value = res.data.message
      matchDistance.value = res.data.distance
      ElMessage.warning('该同学已签到过')
    } else {
      resultStatus.value = 'fail'
      resultMessage.value = res.data.message
      matchDistance.value = null
      ElMessage.warning('🚫 匹配失败！')
    }
  } catch (error: any) {
    resultStatus.value = 'fail'
    resultMessage.value = error.response?.data?.detail || '网络请求错误'
  } finally {
    isChecking.value = false
  }
}

const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
  }
}

// 初始化：获取今日排课列表，然后尝试匹配 URL 参数
onMounted(async () => {
  await fetchSchedulesToday()
  ensureRouteScheduleOption()
  if (urlScheduleId.value) {
    currentScheduleId.value = urlScheduleId.value
    courseTitle.value = urlTitle.value || schedulesToday.value.find(s => s.id === urlScheduleId.value)?.label || ''
  } else if (schedulesToday.value.length > 0) {
    // 无参数时自动选中第一个今日排课
    currentScheduleId.value = schedulesToday.value[0].id
    courseTitle.value = schedulesToday.value[0].label
  } else {
    currentScheduleId.value = null
  }
})

onBeforeUnmount(() => stopCamera())
</script>

<style scoped>
.attendance-container { display: flex; justify-content: center; padding-top: 20px; }
.box-card { width: 700px; text-align: center; }
.check-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.course-info-bar {
  margin-bottom: 16px;
}
.camera-box { background: #000; border-radius: 8px; padding: 10px; margin-bottom: 20px; }
.video-stream { width: 100%; border-radius: 4px; }
.controls { margin-bottom: 20px; }
.result-box { padding: 15px; border-radius: 8px; margin-top: 20px; border: 2px solid; }
.result-box.success { background-color: #f0f9eb; color: #67c23a; border-color: #67c23a; }
.result-box.fail { background-color: #fef0f0; color: #f56c6c; border-color: #f56c6c; }
</style>