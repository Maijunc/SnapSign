<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

// 响应式数据，用于在页面上显示后端返回的信息
const apiMessage = ref('正在尝试连接后端...')
const isSuccess = ref(false)

// 页面挂载时发起请求
onMounted(async () => {
  try {
    // 调用刚才写的 FastAPI 接口
    const response = await axios.get('http://127.0.0.1:8000/api/v1/ping')
    apiMessage.value = response.data.message
    isSuccess.value = true
  } catch (error) {
    apiMessage.value = '连接后端失败，请检查控制台报错或服务是否启动'
    isSuccess.value = false
    console.error("请求报错:", error)
  }
})
</script>

<template>
  <div class="test-container">
    <h1>SnapSign 系统状态</h1>
    <h2 :style="{ color: isSuccess ? '#1890FF' : '#FF4D4F' }">
      {{ apiMessage }}
    </h2>
  </div>
</template>

<style scoped>
.test-container {
  text-align: center;
  margin-top: 100px;
  font-family: sans-serif;
}
</style>