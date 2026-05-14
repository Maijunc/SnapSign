<template>
  <div class="my-attendance-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📋 我的考勤记录</span>
          <el-button type="primary" icon="Refresh" @click="fetchRecords" :loading="isLoading" size="small">
            刷新
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filters.course_id" placeholder="全部课程" clearable style="width: 180px;" @change="onFilterChange">
          <el-option v-for="c in courseOptions" :key="c.course_id" :label="c.course_name" :value="c.course_id" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 120px;" @change="onFilterChange">
          <el-option label="已到" value="present" />
          <el-option label="迟到" value="late" />
          <el-option label="缺勤" value="absent" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px;"
          @change="onFilterChange"
        />
      </div>

      <el-empty v-if="!isLoading && records.length === 0" description="暂无考勤记录" />

      <el-table v-else :data="records" v-loading="isLoading" stripe border style="width: 100%">
        <el-table-column type="index" label="序号" width="70" align="center" :index="indexMethod" />
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column label="签到时间" width="200">
          <template #default="{ row }">
            {{ formatTime(row.check_in_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'present' ? 'success' : row.status === 'late' ? 'warning' : 'danger'"
              size="small"
            >
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="匹配距离" width="120" align="center">
          <template #default="{ row }">
            {{ row.face_distance?.toFixed(3) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <template v-if="appealedIds.has(row.id)">
              <el-tag :type="appealMap.get(row.id)?.status === 'approved' ? 'success' : appealMap.get(row.id)?.status === 'rejected' ? 'danger' : 'warning'" size="small">
                {{ { pending: '待审批', approved: '申诉通过', rejected: '申诉拒绝' }[appealMap.get(row.id)?.status || ''] || '已申诉' }}
              </el-tag>
              <el-tooltip v-if="appealMap.get(row.id)?.reply" :content="'教师回复：' + appealMap.get(row.id)?.reply" placement="top">
                <el-icon style="margin-left: 4px; cursor: pointer; color: #409eff;"><ChatDotRound /></el-icon>
              </el-tooltip>
            </template>
            <el-button
              v-else-if="row.status === 'absent' || row.status === 'late'"
              type="warning"
              size="small"
              text
              @click="openAppealDialog(row)"
            >
              申诉
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar" v-if="total > 0">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchRecords"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>

    <!-- 申诉弹窗 -->
    <el-dialog v-model="appealDialogVisible" title="提交申诉" width="450px">
      <p style="margin-bottom: 10px; color: #606266;">
        课程：{{ appealTarget?.course_name }} · {{ statusText(appealTarget?.status || '') }}
        · {{ formatTime(appealTarget?.check_in_time) }}
      </p>
      <el-input
        v-model="appealReason"
        type="textarea"
        :rows="4"
        placeholder="请说明申诉理由（如人脸识别失败、设备故障等）"
        maxlength="500"
        show-word-limit
      />
      <template #footer>
        <el-button @click="appealDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAppeal" :loading="appealSubmitting">提交申诉</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
import request from '../utils/request'

interface AttendanceRecord {
  id: number
  schedule_id: number
  course_name: string | null
  class_name: string | null
  check_in_time: string | null
  status: string
  face_distance: number | null
}

interface CourseOption {
  course_id: number
  course_name: string
}

const records = ref<AttendanceRecord[]>([])
const total = ref(0)
const isLoading = ref(false)
const courseOptions = ref<CourseOption[]>([])
const appealedIds = ref<Set<number>>(new Set())
const appealMap = ref<Map<number, { status: string; reply: string | null }>>(new Map())

const filters = reactive({
  course_id: null as number | null,
  status: null as string | null,
})
const dateRange = ref<[string, string] | null>(null)
const pagination = reactive({ page: 1, page_size: 20 })

const indexMethod = (index: number) => (pagination.page - 1) * pagination.page_size + index + 1

const fetchRecords = async () => {
  isLoading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filters.course_id) params.course_id = filters.course_id
    if (filters.status) params.status = filters.status
    if (dateRange.value) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await request.get('/api/v1/attendance/my', { params })
    records.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('获取考勤记录失败')
  } finally {
    isLoading.value = false
  }
}

const fetchCourseOptions = async () => {
  try {
    const res = await request.get('/api/v1/courses/my')
    courseOptions.value = res.data.map((c: any) => ({ course_id: c.course_id, course_name: c.course_name }))
    // 去重
    const seen = new Set<number>()
    courseOptions.value = courseOptions.value.filter(c => {
      if (seen.has(c.course_id)) return false
      seen.add(c.course_id)
      return true
    })
  } catch { /* ignore */ }
}

const fetchAppeals = async () => {
  try {
    const res = await request.get('/api/v1/attendance/my_appeals')
    appealedIds.value = new Set(res.data.map((a: any) => a.attendance_id))
    const map = new Map<number, { status: string; reply: string | null }>()
    for (const a of res.data) {
      map.set(a.attendance_id, { status: a.status, reply: a.reply })
    }
    appealMap.value = map
  } catch { /* ignore */ }
}

const onFilterChange = () => {
  pagination.page = 1
  fetchRecords()
}

const onSizeChange = () => {
  pagination.page = 1
  fetchRecords()
}

const statusText = (s: string) => ({ present: '已到', late: '迟到', absent: '缺勤' }[s] || s)
const formatTime = (t: string | null | undefined) => t ? new Date(t).toLocaleString('zh-CN') : '-'

// 申诉
const appealDialogVisible = ref(false)
const appealTarget = ref<AttendanceRecord | null>(null)
const appealReason = ref('')
const appealSubmitting = ref(false)

const openAppealDialog = (row: AttendanceRecord) => {
  appealTarget.value = row
  appealReason.value = ''
  appealDialogVisible.value = true
}

const submitAppeal = async () => {
  if (!appealReason.value.trim()) return ElMessage.warning('请填写申诉理由')
  if (!appealTarget.value) return
  appealSubmitting.value = true
  try {
    await request.post('/api/v1/attendance/appeal', {
      attendance_id: appealTarget.value.id,
      reason: appealReason.value,
    })
    ElMessage.success('申诉已提交')
    appealDialogVisible.value = false
    appealedIds.value.add(appealTarget.value.id)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '申诉提交失败')
  } finally {
    appealSubmitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchRecords(), fetchCourseOptions(), fetchAppeals()])
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
