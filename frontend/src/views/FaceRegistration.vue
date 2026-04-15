<template>
  <div class="registration-container">
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card shadow="hover" header="📷 实时人脸采集">
          <div class="camera-box" v-loading="isCameraStarting" element-loading-text="正在唤醒摄像头...">
            <video ref="videoRef" autoplay playsinline class="video-stream"></video>
            <canvas ref="canvasRef" style="display: none;"></canvas>
            
            <div class="camera-controls">
              <el-button type="primary" @click="startCamera" :disabled="isCameraReady">启动摄像头</el-button>
              <el-button type="danger" @click="stopCamera" :disabled="!isCameraReady">关闭摄像头</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="hover" header="📝 档案录入与特征提取">
          <el-form :model="studentForm" label-width="80px" class="reg-form">
            <el-form-item label="学号" required>
              <el-input v-model="studentForm.studentId" placeholder="例如：2022414120219" />
            </el-form-item>
            <el-form-item label="姓名" required>
              <el-input v-model="studentForm.name" placeholder="请输入学生姓名" />
            </el-form-item>
            
            <div class="preview-box" v-if="capturedImage">
              <p class="preview-title">已抓拍特征图像：</p>
              <img :src="capturedImage" class="preview-img" />
            </div>
            
            <el-form-item style="margin-top: 30px;">
              <el-button type="success" size="large" @click="captureAndSubmit" :disabled="!isCameraReady">
                抓拍并录入系统
              </el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

// 摄像头与画布引用
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

// 状态控制
const isCameraStarting = ref(false)
const isCameraReady = ref(false)
const capturedImage = ref<string | null>(null)

// 表单数据
const studentForm = reactive({
  studentId: '',
  name: ''
})

// 保存视频流对象，方便后面关闭
let mediaStream: MediaStream | null = null

// 启动摄像头
const startCamera = async () => {
  isCameraStarting.value = true
  try {
    // 调用浏览器底层的媒体设备接口
    mediaStream = await navigator.mediaDevices.getUserMedia({ 
      video: { width: 640, height: 480 } 
    })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      isCameraReady.value = true
      ElMessage.success('摄像头已成功唤醒！')
    }
  } catch (error) {
    ElMessage.error('无法访问摄像头，请检查浏览器权限！')
    console.error('Camera error:', error)
  } finally {
    isCameraStarting.value = false
  }
}

// 关闭摄像头
const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    if (videoRef.value) videoRef.value.srcObject = null
    isCameraReady.value = false
    mediaStream = null
  }
}

// 抓拍并模拟提交
const captureAndSubmit = () => {
  if (!studentForm.studentId || !studentForm.name) {
    ElMessage.warning('请先填写学号和姓名！')
    return
  }
  
  const video = videoRef.value
  const canvas = canvasRef.value
  if (video && canvas) {
    // 将视频当前帧画到 canvas 上
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx?.drawImage(video, 0, 0, canvas.width, canvas.height)
    
    // 将 canvas 转化为 base64 图片格式
    capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)
    
    // TODO: 这里未来会用 Axios 把数据发给 FastAPI 后端
    console.log('提交的数据：', {
      studentId: studentForm.studentId,
      name: studentForm.name,
      imageFeature: 'Base64Image...' // 这里省略长字符串
    })
    
    ElMessage.success(`✅ 抓拍成功！准备提取 ${studentForm.name} 的特征向量。`)
  }
}

// 重置表单
const resetForm = () => {
  studentForm.studentId = ''
  studentForm.name = ''
  capturedImage.value = null
}

// 离开页面时自动关闭摄像头，防止后台偷拍
onBeforeUnmount(() => {
  stopCamera()
})
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
.video-stream {
  width: 100%;
  max-width: 640px;
  border-radius: 4px;
  background-color: #2c3e50;
  aspect-ratio: 4/3;
}
.camera-controls {
  margin-top: 15px;
}
.reg-form {
  margin-top: 20px;
}
.preview-box {
  margin-top: 20px;
  text-align: center;
  border: 1px dashed #d9d9d9;
  padding: 10px;
  border-radius: 6px;
}
.preview-title {
  color: #606266;
  font-size: 14px;
  margin-bottom: 10px;
}
.preview-img {
  max-width: 100%;
  border-radius: 4px;
}
</style>