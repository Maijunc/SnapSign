<template>
  <div class="approval-container">
    <el-tabs v-model="activeTab" type="border-card" @tab-change="onTabChange">
      <!-- 考勤申诉 -->
      <el-tab-pane name="appeals">
        <template #label>
          考勤申诉
          <el-badge v-if="appealPendingCount > 0" :value="appealPendingCount" :max="99" class="tab-badge" />
        </template>

        <div class="filter-bar">
          <el-select v-model="appealFilter.status" placeholder="状态" style="width: 130px;" @change="fetchAppeals">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="全部" value="all" />
          </el-select>
          <el-select v-model="appealFilter.course_id" placeholder="全部课程" clearable style="width: 200px;" @change="fetchAppeals">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button icon="Refresh" @click="fetchAppeals" :loading="appealLoading" style="margin-left: auto;">刷新</el-button>
        </div>

        <el-table :data="appeals" stripe border v-loading="appealLoading" style="width: 100%; margin-top: 12px;">
          <el-table-column prop="student_name" label="学生" width="90" />
          <el-table-column prop="course_name" label="课程" min-width="120" />
          <el-table-column prop="class_name" label="班级" width="120" />
          <el-table-column label="原考勤状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="row.original_status === 'absent' ? 'danger' : 'warning'" size="small">
                {{ statusTextMap[row.original_status] || row.original_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="签到时间" width="170">
            <template #default="{ row }">
              {{ row.check_in_time ? new Date(row.check_in_time).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="申诉理由" min-width="180" show-overflow-tooltip />
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">
              {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="reviewTagType(row.status)" size="small">{{ reviewStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reply" label="回复" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button type="success" size="small" @click="openReviewDialog(row, 'appeal', 'approved')">通过</el-button>
                <el-button type="danger" size="small" @click="openReviewDialog(row, 'appeal', 'rejected')">拒绝</el-button>
              </template>
              <span v-else style="color: #999;">已处理</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 请假申请 -->
      <el-tab-pane name="leaves">
        <template #label>
          请假申请
          <el-badge v-if="leavePendingCount > 0" :value="leavePendingCount" :max="99" class="tab-badge" />
        </template>

        <div class="filter-bar">
          <el-select v-model="leaveFilter.status" placeholder="状态" style="width: 130px;" @change="fetchLeaves">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="全部" value="all" />
          </el-select>
          <el-select v-model="leaveFilter.course_id" placeholder="全部课程" clearable style="width: 200px;" @change="fetchLeaves">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button icon="Refresh" @click="fetchLeaves" :loading="leaveLoading" style="margin-left: auto;">刷新</el-button>
        </div>

        <el-table :data="leaves" stripe border v-loading="leaveLoading" style="width: 100%; margin-top: 12px;">
          <el-table-column prop="student_name" label="学生" width="90" />
          <el-table-column prop="course_name" label="课程" min-width="120" />
          <el-table-column prop="class_name" label="班级" width="120" />
          <el-table-column prop="leave_date" label="请假日期" width="120" />
          <el-table-column prop="reason" label="请假理由" min-width="180" show-overflow-tooltip />
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">
              {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="reviewTagType(row.status)" size="small">{{ reviewStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reply" label="回复" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button type="success" size="small" @click="openReviewDialog(row, 'leave', 'approved')">通过</el-button>
                <el-button type="danger" size="small" @click="openReviewDialog(row, 'leave', 'rejected')">拒绝</el-button>
              </template>
              <span v-else style="color: #999;">已处理</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 审批弹窗 -->
    <el-dialog v-model="reviewDialogVisible" :title="reviewAction === 'approved' ? '✅ 确认通过' : '❌ 确认拒绝'" width="450px">
      <el-form label-width="80px">
        <el-form-item label="学生">{{ reviewTarget?.student_name }}</el-form-item>
        <el-form-item label="课程">{{ reviewTarget?.course_name }}</el-form-item>
        <el-form-item :label="reviewType === 'appeal' ? '申诉理由' : '请假理由'">
          <span style="color: #606266;">{{ reviewTarget?.reason }}</span>
        </el-form-item>
        <el-form-item label="回复意见">
          <el-input v-model="reviewReply" type="textarea" :rows="3" placeholder="可选，填写审批意见" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button :type="reviewAction === 'approved' ? 'success' : 'danger'" @click="submitReview" :loading="reviewSubmitting">
          {{ reviewAction === 'approved' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

interface AppealItem {
  id: number
  attendance_id: number
  reason: string
  status: string
  reply: string | null
  created_at: string | null
  course_name: string | null
  class_name: string | null
  student_name: string | null
  original_status: string | null
  check_in_time: string | null
}

interface LeaveItem {
  id: number
  schedule_id: number
  leave_date: string
  reason: string
  status: string
  reply: string | null
  created_at: string | null
  course_name: string | null
  class_name: string | null
  student_name: string | null
}

interface CourseOption { id: number; name: string }

const activeTab = ref('appeals')
const courses = ref<CourseOption[]>([])

// ---------- 申诉 ----------
const appeals = ref<AppealItem[]>([])
const appealLoading = ref(false)
const appealPendingCount = ref(0)
const appealFilter = reactive({ status: 'pending', course_id: null as number | null })

// ---------- 请假 ----------
const leaves = ref<LeaveItem[]>([])
const leaveLoading = ref(false)
const leavePendingCount = ref(0)
const leaveFilter = reactive({ status: 'pending', course_id: null as number | null })

// ---------- 审批弹窗 ----------
const reviewDialogVisible = ref(false)
const reviewSubmitting = ref(false)
const reviewTarget = ref<AppealItem | LeaveItem | null>(null)
const reviewType = ref<'appeal' | 'leave'>('appeal')
const reviewAction = ref<'approved' | 'rejected'>('approved')
const reviewReply = ref('')

const statusTextMap: Record<string, string> = { present: '正常', late: '迟到', absent: '缺勤' }
const reviewStatusText = (s: string) => ({ pending: '待审批', approved: '已通过', rejected: '已拒绝' }[s] || s)
const reviewTagType = (s: string) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info') as any

// ---------- 获取课程列表（用于过滤器） ----------
const fetchCourses = async () => {
  try {
    const res = await request.get('/api/v1/courses')
    courses.value = res.data.map((c: any) => ({ id: c.id, name: c.name }))
  } catch { /* ignore */ }
}

// ---------- 获取申诉列表 ----------
const fetchAppeals = async () => {
  appealLoading.value = true
  try {
    const params: any = { status: appealFilter.status }
    if (appealFilter.course_id) params.course_id = appealFilter.course_id
    const res = await request.get('/api/v1/appeals/pending', { params })
    appeals.value = res.data
  } catch {
    ElMessage.error('获取申诉列表失败')
  } finally {
    appealLoading.value = false
  }
}

// ---------- 获取请假列表 ----------
const fetchLeaves = async () => {
  leaveLoading.value = true
  try {
    const params: any = { status: leaveFilter.status }
    if (leaveFilter.course_id) params.course_id = leaveFilter.course_id
    const res = await request.get('/api/v1/leaves/pending', { params })
    leaves.value = res.data
  } catch {
    ElMessage.error('获取请假列表失败')
  } finally {
    leaveLoading.value = false
  }
}

// ---------- 获取待审批计数（用于 badge） ----------
const fetchPendingCounts = async () => {
  try {
    const [aRes, lRes] = await Promise.all([
      request.get('/api/v1/appeals/pending', { params: { status: 'pending' } }),
      request.get('/api/v1/leaves/pending', { params: { status: 'pending' } }),
    ])
    appealPendingCount.value = aRes.data.length
    leavePendingCount.value = lRes.data.length
  } catch { /* ignore */ }
}

// ---------- 打开审批弹窗 ----------
const openReviewDialog = (row: any, type: 'appeal' | 'leave', action: 'approved' | 'rejected') => {
  reviewTarget.value = row
  reviewType.value = type
  reviewAction.value = action
  reviewReply.value = ''
  reviewDialogVisible.value = true
}

// ---------- 提交审批 ----------
const submitReview = async () => {
  if (!reviewTarget.value) return
  reviewSubmitting.value = true
  try {
    const id = reviewTarget.value.id
    const url = reviewType.value === 'appeal'
      ? `/api/v1/appeals/${id}/review`
      : `/api/v1/leaves/${id}/review`
    await request.put(url, {
      action: reviewAction.value,
      reply: reviewReply.value,
    })
    ElMessage.success(reviewAction.value === 'approved' ? '已通过' : '已拒绝')
    reviewDialogVisible.value = false
    // 刷新当前列表和计数
    if (reviewType.value === 'appeal') fetchAppeals()
    else fetchLeaves()
    fetchPendingCounts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '审批失败')
  } finally {
    reviewSubmitting.value = false
  }
}

const onTabChange = () => {
  if (activeTab.value === 'appeals') fetchAppeals()
  else fetchLeaves()
}

onMounted(() => {
  fetchCourses()
  fetchAppeals()
  fetchLeaves()
  fetchPendingCounts()
})
</script>

<style scoped>
.approval-container {
  padding: 0;
}
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tab-badge {
  margin-left: 6px;
  vertical-align: middle;
}
</style>
