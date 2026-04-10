<template>
  <div class="dashboard-container">
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6" v-for="(stat, index) in stats" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" :style="{ color: stat.color }"><component :is="stat.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-title">{{ stat.title }}</div>
              <div class="stat-value">{{ stat.value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card shadow="hover" header="本周出勤趋势">
          <div ref="chartRef" style="height: 350px; width: 100%;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" header="实时考勤动态 (Mock)">
          <el-timeline>
            <el-timeline-item
              v-for="(activity, index) in recentActivities"
              :key="index"
              :type="activity.type"
              :timestamp="activity.time"
            >
              {{ activity.name }} - {{ activity.action }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from 'vue'
import { User, Check, Warning, Close } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

// --- Mock 假数据区（等后端接口好了再替换） ---

const stats = ref([
  { title: '学生总数', value: '45 人', icon: shallowRef(User), color: '#409EFF' },
  { title: '今日已签到', value: '38 人', icon: shallowRef(Check), color: '#67C23A' },
  { title: '迟到/异常', value: '3 人', icon: shallowRef(Warning), color: '#E6A23C' },
  { title: '缺勤', value: '4 人', icon: shallowRef(Close), color: '#F56C6C' },
])

const recentActivities = ref([
  { name: '麦天骏', action: '签到成功 (人脸比对通过)', time: '08:52:10', type: 'success' },
  { name: '李雷', action: '签到成功 (人脸比对通过)', time: '08:53:45', type: 'success' },
  { name: '韩梅梅', action: '迟到 (09:05 补卡)', time: '09:05:12', type: 'warning' },
  { name: 'Unknown', action: '防伪拦截 (识别失败)', time: '09:15:30', type: 'danger' },
])

// --- ECharts 图表初始化 ---
const chartRef = ref<HTMLDivElement | null>(null)

onMounted(() => {
  if (chartRef.value) {
    const myChart = echarts.init(chartRef.value)
    const option = {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五'] },
      yAxis: { type: 'value', name: '出勤率(%)', min: 0, max: 100 },
      series: [
        {
          data: [95, 92, 98, 85, 90],
          type: 'line',
          smooth: true,
          areaStyle: { color: 'rgba(64,158,255,0.2)' },
          itemStyle: { color: '#409EFF' }
        }
      ]
    }
    myChart.setOption(option)
    // 监听窗口缩放，自适应图表
    window.addEventListener('resize', () => myChart.resize())
  }
})
</script>

<style scoped>
.stat-content {
  display: flex;
  align-items: center;
}
.stat-icon {
  font-size: 48px;
  margin-right: 20px;
}
.stat-info {
  display: flex;
  flex-direction: column;
}
.stat-title {
  font-size: 14px;
  color: #909399;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-top: 5px;
}
</style>