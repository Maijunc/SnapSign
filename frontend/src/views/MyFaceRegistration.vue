<template>
  <div class="my-face-container">
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card shadow="hover" header="📷 人脸采集">
          <div class="camera-box" v-loading="isCameraStarting" element-loading-text="正在唤醒摄像头...">
            <div class="video-wrapper">
              <video ref="videoRef" autoplay playsinline class="video-stream"></video>
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
            
            <!-- 拍照提示 -->
            <div class="capture-tips" v-if="isCameraReady">
              <el-tag type="info" size="small">请将面部对准椭圆框内</el-tag>
              <el-tag type="info" size="small">确保光线充足、面部无遮挡</el-tag>
              <el-tag type="info" size="small">请摘下口罩、墨镜等遮挡物</el-tag>
            </div>

            <div class="camera-controls">
              <el-button type="primary" @click="startCamera" :disabled="isCameraReady">启动摄像头</el-button>
              <el-button type="danger" @click="stopCamera" :disabled="!isCameraReady">关闭摄像头</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="hover" header="📝 我的人脸信息">
          <!-- 已录入状态 -->
          <template v-if="faceRegistered">
            <el-result icon="success" title="人脸已录入" sub-title="你的人脸特征已成功注册，可正常参与考勤签到" />
            <div class="registered-photo" v-if="registeredImage">
              <p style="color: #606266; font-size: 14px; margin-bottom: 8px; text-align: center;">已录入的照片：</p>
              <img :src="registeredImage" class="preview-img" />
            </div>
            <el-button type="warning" style="width: 100%; margin-top: 16px;" @click="reRegister">重新录入</el-button>
          </template>

          <!-- 未录入状态 -->
          <template v-else>
            <el-descriptions :column="1" border style="margin-bottom: 20px;">
              <el-descriptions-item label="学号">{{ studentId }}</el-descriptions-item>
              <el-descriptions-item label="姓名">{{ studentName }}</el-descriptions-item>
            </el-descriptions>

            <div class="preview-box" v-if="capturedImage">
              <p class="preview-title">已抓拍图像：</p>
              <img :src="capturedImage" class="preview-img" />
            </div>
            
            <el-button 
              type="success" size="large" style="width: 100%; margin-top: 20px;"
              @click="captureAndSubmit" 
              :disabled="!isCameraReady"
              :loading="isSubmitting"
            >
              抓拍并注册人脸
            </el-button>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isCameraStarting = ref(false)
const isCameraReady = ref(false)
const isSubmitting = ref(false)
const capturedImage = ref<string | null>(null)
const faceRegistered = ref(false)
const registeredImage = ref<string | null>(null)

// 学生信息（从登录态自动获取）
const studentId = ref('')
const studentName = ref('')

let mediaStream: MediaStream | null = null

const fetchMyInfo = async () => {
  try {
    const res = await request.get('/api/v1/auth/me')
    studentId.value = res.data.username  // 学号即账号
    studentName.value = res.data.real_name
  } catch {
    ElMessage.error('获取用户信息失败')
  }
}

const checkFaceStatus = async () => {
  try {
    const res = await request.get('/api/v1/faces/my_status')
    faceRegistered.value = res.data.registered
  } catch { /* 静默 */ }
}

const startCamera = async () => {
  isCameraStarting.value = true
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      isCameraReady.value = true
      ElMessage.success('摄像头已启动')
    }
  } catch {
    ElMessage.error('无法访问摄像头，请检查浏览器权限！')
  } finally {
    isCameraStarting.value = false
  }
}

const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    if (videoRef.value) videoRef.value.srcObject = null
    isCameraReady.value = false
    mediaStream = null
  }
}

const captureAndSubmit = async () => {
  if (!studentId.value) return ElMessage.warning('用户信息未加载，请刷新页面')

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
      student_id: studentId.value,
      name: studentName.value,
      image_base64: capturedImage.value,
    })
    if (res.data.status === 'success') {
      ElMessage.success('人脸注册成功！')
      faceRegistered.value = true
      registeredImage.value = capturedImage.value
      // 缓存照片到本地
      if (capturedImage.value) localStorage.setItem('facePhoto', capturedImage.value)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '注册失败')
  } finally {
    isSubmitting.value = false
  }
}

const reRegister = async () => {
  await ElMessageBox.confirm('重新录入将覆盖现有的人脸特征，确认继续？', '提示', { type: 'warning' })
  faceRegistered.value = false
}

onMounted(async () => {
  await fetchMyInfo()
  await checkFaceStatus()
  // 加载缓存的已注册照片
  if (faceRegistered.value) {
    registeredImage.value = localStorage.getItem('facePhoto')
  }
})

onBeforeUnmount(() => stopCamera())
</script>

<style scoped>
.camera-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  background-color: #000;
  border-radius: 8px;
  padding: 10px;
}
.video-wrapper {
  position: relative;
  width: 100%;
  max-width: 640px;
}
.video-stream {
  width: 100%;
  max-width: 640px;
  border-radius: 4px;
  background-color: #2c3e50;
  aspect-ratio: 4/3;
  display: block;
}
.face-guide-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.face-guide-svg {
  width: 100%;
  height: 100%;
}
.capture-tips {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
.camera-controls { margin-top: 15px; }
.preview-box {
  margin-top: 15px;
  text-align: center;
  border: 1px dashed #d9d9d9;
  padding: 10px;
  border-radius: 6px;
}
.preview-title { color: #606266; font-size: 14px; margin-bottom: 8px; }
.preview-img { max-width: 100%; border-radius: 4px; }
.registered-photo {
  text-align: center;
  border: 1px solid #e4e7ed;
  padding: 12px;
  border-radius: 8px;
  background: #fafafa;
}
</style>
