<template>
  <div class="attendance-container">
    <!-- 未携带 scheduleId 时的提示 -->
    <el-card v-if="!scheduleId" shadow="hover" class="box-card" style="text-align: center;">
      <el-empty description="请从「我的课程」页面选择一节课后，再开启打卡机">
        <el-button type="primary" @click="$router.push('/courses')">前往我的课程</el-button>
      </el-empty>
    </el-card>

    <!-- 正常打卡界面 -->
    <el-card v-else shadow="hover" class="box-card">
      <template #header>
        <span>🕒 课堂自动打卡机 — {{ courseTitle }}</span>
      </template>

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
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const route = useRoute()
const scheduleId = computed(() => Number(route.query.scheduleId) || 0)
const courseTitle = computed(() => (route.query.title as string) || '未知课程')

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
  } catch (error) {
    ElMessage.error('无法唤醒摄像头！')
  }
}

const checkIn = async () => {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  // 抓拍
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d')?.drawImage(video, 0, 0)
  const base64Image = canvas.toDataURL('image/jpeg', 0.9)

  isChecking.value = true
  resultMessage.value = ''
  
  try {
    const res = await request.post('/api/v1/faces/check_in', {
      image_base64: base64Image,
      schedule_id: scheduleId.value,
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
onBeforeUnmount(() => stopCamera())
</script>

<style scoped>
.attendance-container { display: flex; justify-content: center; padding-top: 20px; }
.box-card { width: 700px; text-align: center; }
.camera-box { background: #000; border-radius: 8px; padding: 10px; margin-bottom: 20px; }
.video-stream { width: 100%; border-radius: 4px; }
.controls { margin-bottom: 20px; }
.result-box { padding: 15px; border-radius: 8px; margin-top: 20px; border: 2px solid; }
.result-box.success { background-color: #f0f9eb; color: #67c23a; border-color: #67c23a; }
.result-box.fail { background-color: #fef0f0; color: #f56c6c; border-color: #f56c6c; }
</style>