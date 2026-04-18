<template>
  <div class="management-container">
    <el-card shadow="hover" header="👨‍🎓 学生人脸档案管理">
      <div class="action-bar">
        <el-button type="primary" icon="Refresh" @click="fetchStudents" :loading="isLoading">
          刷新档案列表
        </el-button>
        <span class="total-count">当前系统已录入：{{ studentList.length }} 人</span>
      </div>

      <el-table :data="studentList" style="width: 100%" v-loading="isLoading" border stripe>
        <el-table-column type="index" label="序号" width="80" align="center" />
        <el-table-column prop="student_id" label="学号" width="200" align="center" />
        <el-table-column prop="name" label="姓名" min-width="150" align="center">
          <template #default="scope">
            <strong>{{ scope.row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="特征状态" width="150" align="center">
          <template #default>
            <el-tag type="success">128维特征已存</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-popconfirm
              title="确定要删除该学生的人脸档案吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="handleDelete(scope.row.student_id)"
            >
              <template #reference>
                <el-button type="danger" size="small" icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
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

// 响应式状态
const studentList = ref([])
const isLoading = ref(false)

// 页面一加载就去后端拉取数据
onMounted(() => {
  fetchStudents()
})

// 拉取学生列表
const fetchStudents = async () => {
  isLoading.value = true
  try {
    const res = await request.get('/api/v1/students')
    if (res.data.status === 'success') {
      studentList.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('无法连接后端获取数据！')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// 删除指定学生
const handleDelete = async (studentId: string) => {
  try {
    const res = await request.delete(`/api/v1/students/${studentId}`)
    if (res.data.status === 'success') {
      ElMessage.success(res.data.message)
      // 删除成功后，重新拉取最新列表
      fetchStudents()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败！')
  }
}
</script>

<style scoped>
.management-container {
  padding-top: 10px;
}
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.total-count {
  color: #606266;
  font-size: 14px;
}
</style>