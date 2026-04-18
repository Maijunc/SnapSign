<template>
  <div class="course-management-container">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- ========== 班级管理 ========== -->
      <el-tab-pane label="班级管理" name="classes">
        <div class="tab-header">
          <el-input v-model="newClassName" placeholder="输入新班级名称" style="width: 280px; margin-right: 10px;" />
          <el-button type="primary" @click="createClass" :loading="classLoading">新增班级</el-button>
        </div>
        <el-table :data="classList" stripe border style="width: 100%; margin-top: 15px;" v-loading="classLoading">
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="id" label="ID" width="80" align="center" />
          <el-table-column prop="name" label="班级名称" />
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openClassStudents(row)">管理学生</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ========== 课程管理 ========== -->
      <el-tab-pane label="课程管理" name="courses">
        <div class="tab-header">
          <el-button type="primary" icon="Plus" @click="openCourseDialog">新增课程</el-button>
        </div>
        <el-table :data="courseList" stripe border style="width: 100%; margin-top: 15px;" v-loading="courseLoading">
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="name" label="课程名称" width="200" />
          <el-table-column prop="teacher_name" label="授课教师" width="150" />
          <el-table-column label="关联班级">
            <template #default="{ row }">
              <el-tag v-for="c in row.classes" :key="c.id" size="small" style="margin-right: 5px;">{{ c.name }}</el-tag>
              <span v-if="!row.classes?.length" style="color: #999;">未分配</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ========== 排课管理 ========== -->
      <el-tab-pane label="排课管理" name="schedules">
        <div class="tab-header">
          <el-button type="primary" icon="Plus" @click="openScheduleDialog">新增排课</el-button>
        </div>
        <el-table :data="scheduleList" stripe border style="width: 100%; margin-top: 15px;" v-loading="scheduleLoading">
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="course_name" label="课程" width="150" />
          <el-table-column prop="class_name" label="班级" width="150" />
          <el-table-column label="星期" width="100">
            <template #default="{ row }">{{ weekdayText(row.weekday) }}</template>
          </el-table-column>
          <el-table-column label="首次上课" width="130">
            <template #default="{ row }">{{ row.start_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="周数" width="80" align="center">
            <template #default="{ row }">{{ row.total_weeks ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="时间" width="180">
            <template #default="{ row }">{{ row.start_time }} ~ {{ row.end_time }}</template>
          </el-table-column>
          <el-table-column prop="location" label="教室" />
        </el-table>
      </el-tab-pane>

      <!-- ========== 节假日管理 ========== -->
      <el-tab-pane label="节假日管理" name="holidays">
        <div class="tab-header">
          <el-date-picker v-model="newHolidayDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 180px; margin-right: 10px;" />
          <el-input v-model="newHolidayName" placeholder="节假日名称" style="width: 200px; margin-right: 10px;" />
          <el-button type="primary" @click="createHoliday" :loading="holidayLoading">添加节假日</el-button>
        </div>
        <el-table :data="holidayList" stripe border style="width: 100%; margin-top: 15px;" v-loading="holidayLoading">
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="holiday_date" label="日期" width="150" />
          <el-table-column prop="name" label="名称" />
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteHoliday(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增课程弹窗 -->
    <el-dialog v-model="courseDialogVisible" title="新增课程" width="450px">
      <el-form :model="courseForm" label-width="80px">
        <el-form-item label="课程名称">
          <el-input v-model="courseForm.name" placeholder="如：高等数学" />
        </el-form-item>
        <el-form-item label="授课教师">
          <el-select v-model="courseForm.teacher_id" placeholder="选择教师" style="width: 100%">
            <el-option v-for="t in teacherList" :key="t.id" :label="t.real_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联班级">
          <el-select v-model="courseForm.class_ids" multiple placeholder="可多选" style="width: 100%">
            <el-option v-for="c in classList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createCourse" :loading="courseSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增排课弹窗 -->
    <el-dialog v-model="scheduleDialogVisible" title="新增排课" width="450px">
      <el-form :model="scheduleForm" label-width="100px">
        <el-form-item label="课程">
          <el-select v-model="scheduleForm.course_id" placeholder="选择课程" style="width: 100%">
            <el-option v-for="c in courseList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="scheduleForm.class_id" placeholder="选择班级" style="width: 100%">
            <el-option v-for="c in classList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="首次上课日期">
          <el-date-picker v-model="scheduleForm.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="持续周数">
          <el-input-number v-model="scheduleForm.total_weeks" :min="1" :max="30" />
        </el-form-item>
        <el-form-item label="上课时间">
          <el-time-picker v-model="scheduleForm.start_time" format="HH:mm" value-format="HH:mm:ss" placeholder="上课时间" />
        </el-form-item>
        <el-form-item label="下课时间">
          <el-time-picker v-model="scheduleForm.end_time" format="HH:mm" value-format="HH:mm:ss" placeholder="下课时间" />
        </el-form-item>
        <el-form-item label="教室">
          <el-input v-model="scheduleForm.location" placeholder="如：教学楼A-301" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createSchedule" :loading="scheduleSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 管理班级学生弹窗 -->
    <el-dialog v-model="classStudentDialogVisible" :title="`管理学生 - ${currentClass?.name || ''}`" width="600px">
      <div style="margin-bottom: 15px; display: flex; gap: 10px;">
        <el-select v-model="selectedStudentIds" multiple filterable placeholder="选择学生添加到班级" style="flex: 1;">
          <el-option v-for="s in allStudents" :key="s.id" :label="`${s.name} (${s.student_id})`" :value="s.id" />
        </el-select>
        <el-button type="primary" @click="addStudentsToClass" :loading="classStudentLoading">添加</el-button>
      </div>
      <el-table :data="classStudents" stripe border v-loading="classStudentLoading">
        <el-table-column prop="student_id" label="学号" width="150" />
        <el-table-column prop="name" label="姓名" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="removeStudentFromClass(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const activeTab = ref('classes')

// ===== 班级 =====
const classList = ref<any[]>([])
const classLoading = ref(false)
const newClassName = ref('')

const fetchClasses = async () => {
  classLoading.value = true
  try {
    const res = await request.get('/api/v1/classes')
    classList.value = res.data
  } catch { ElMessage.error('获取班级列表失败') }
  finally { classLoading.value = false }
}

const createClass = async () => {
  if (!newClassName.value.trim()) return ElMessage.warning('请输入班级名称')
  classLoading.value = true
  try {
    await request.post('/api/v1/classes', { name: newClassName.value.trim() })
    ElMessage.success('班级创建成功')
    newClassName.value = ''
    fetchClasses()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
  finally { classLoading.value = false }
}

// ===== 课程 =====
const courseList = ref<any[]>([])
const courseLoading = ref(false)
const courseDialogVisible = ref(false)
const courseSubmitting = ref(false)
const teacherList = ref<any[]>([])

const courseForm = reactive({ name: '', teacher_id: null as number | null, class_ids: [] as number[] })

const fetchCourses = async () => {
  courseLoading.value = true
  try {
    const res = await request.get('/api/v1/courses')
    courseList.value = res.data
  } catch { ElMessage.error('获取课程列表失败') }
  finally { courseLoading.value = false }
}

const fetchTeachers = async () => {
  try {
    const res = await request.get('/api/v1/users')
    teacherList.value = res.data.filter((u: any) => u.role === 'teacher')
  } catch { /* 静默 */ }
}

const openCourseDialog = () => {
  courseForm.name = ''
  courseForm.teacher_id = null
  courseForm.class_ids = []
  fetchTeachers()
  courseDialogVisible.value = true
}

const createCourse = async () => {
  if (!courseForm.name || !courseForm.teacher_id) return ElMessage.warning('请填写完整信息')
  courseSubmitting.value = true
  try {
    await request.post('/api/v1/courses', {
      name: courseForm.name,
      teacher_id: courseForm.teacher_id,
      class_ids: courseForm.class_ids,
    })
    ElMessage.success('课程创建成功')
    courseDialogVisible.value = false
    fetchCourses()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
  finally { courseSubmitting.value = false }
}

// ===== 排课 =====
const scheduleList = ref<any[]>([])
const scheduleLoading = ref(false)
const scheduleDialogVisible = ref(false)
const scheduleSubmitting = ref(false)

const scheduleForm = reactive({
  course_id: null as number | null,
  class_id: null as number | null,
  start_date: '',
  total_weeks: 16,
  start_time: '',
  end_time: '',
  location: '',
})

const fetchSchedules = async () => {
  scheduleLoading.value = true
  try {
    const all: any[] = []
    for (const c of courseList.value) {
      const res = await request.get(`/api/v1/courses/${c.id}/schedules`)
      all.push(...res.data)
    }
    scheduleList.value = all
  } catch { ElMessage.error('获取排课列表失败') }
  finally { scheduleLoading.value = false }
}

const openScheduleDialog = () => {
  scheduleForm.course_id = null
  scheduleForm.class_id = null
  scheduleForm.start_date = ''
  scheduleForm.total_weeks = 16
  scheduleForm.start_time = ''
  scheduleForm.end_time = ''
  scheduleForm.location = ''
  scheduleDialogVisible.value = true
}

const createSchedule = async () => {
  if (!scheduleForm.course_id || !scheduleForm.class_id || !scheduleForm.start_date || !scheduleForm.start_time || !scheduleForm.end_time) {
    return ElMessage.warning('请填写完整信息')
  }
  scheduleSubmitting.value = true
  try {
    await request.post('/api/v1/schedules', {
      course_id: scheduleForm.course_id,
      class_id: scheduleForm.class_id,
      start_date: scheduleForm.start_date,
      total_weeks: scheduleForm.total_weeks,
      start_time: scheduleForm.start_time,
      end_time: scheduleForm.end_time,
      location: scheduleForm.location,
    })
    ElMessage.success('排课创建成功')
    scheduleDialogVisible.value = false
    fetchSchedules()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
  finally { scheduleSubmitting.value = false }
}

// ===== 节假日 =====
const holidayList = ref<any[]>([])
const holidayLoading = ref(false)
const newHolidayDate = ref('')
const newHolidayName = ref('')

const fetchHolidays = async () => {
  holidayLoading.value = true
  try {
    const res = await request.get('/api/v1/holidays')
    holidayList.value = res.data
  } catch { ElMessage.error('获取节假日失败') }
  finally { holidayLoading.value = false }
}

const createHoliday = async () => {
  if (!newHolidayDate.value || !newHolidayName.value.trim()) return ElMessage.warning('请填写日期和名称')
  holidayLoading.value = true
  try {
    await request.post('/api/v1/holidays', { holiday_date: newHolidayDate.value, name: newHolidayName.value.trim() })
    ElMessage.success('节假日添加成功')
    newHolidayDate.value = ''
    newHolidayName.value = ''
    fetchHolidays()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '添加失败') }
  finally { holidayLoading.value = false }
}

const deleteHoliday = async (row: any) => {
  await ElMessageBox.confirm(`确认删除 ${row.name}？`, '提示', { type: 'warning' })
  holidayLoading.value = true
  try {
    await request.delete(`/api/v1/holidays/${row.id}`)
    ElMessage.success('已删除')
    fetchHolidays()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '删除失败') }
  finally { holidayLoading.value = false }
}

// ===== 班级学生管理 =====
const classStudentDialogVisible = ref(false)
const classStudentLoading = ref(false)
const currentClass = ref<any>(null)
const classStudents = ref<any[]>([])
const allStudents = ref<any[]>([])
const selectedStudentIds = ref<number[]>([])

const openClassStudents = async (cls: any) => {
  currentClass.value = cls
  selectedStudentIds.value = []
  classStudentDialogVisible.value = true
  await Promise.all([fetchClassStudents(cls.id), fetchAllStudents()])
}

const fetchClassStudents = async (classId: number) => {
  classStudentLoading.value = true
  try {
    const res = await request.get(`/api/v1/classes/${classId}/students`)
    classStudents.value = res.data
  } catch { ElMessage.error('获取班级学生失败') }
  finally { classStudentLoading.value = false }
}

const fetchAllStudents = async () => {
  try {
    const res = await request.get('/api/v1/students')
    allStudents.value = res.data?.data || res.data || []
  } catch { /* 静默 */ }
}

const addStudentsToClass = async () => {
  if (!selectedStudentIds.value.length) return ElMessage.warning('请选择学生')
  classStudentLoading.value = true
  try {
    await request.post(`/api/v1/classes/${currentClass.value.id}/students`, { student_feature_ids: selectedStudentIds.value })
    ElMessage.success('添加成功')
    selectedStudentIds.value = []
    fetchClassStudents(currentClass.value.id)
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '添加失败') }
  finally { classStudentLoading.value = false }
}

const removeStudentFromClass = async (row: any) => {
  await ElMessageBox.confirm(`确认将 ${row.name} 移出班级？`, '提示', { type: 'warning' })
  classStudentLoading.value = true
  try {
    await request.delete(`/api/v1/classes/${currentClass.value.id}/students/${row.id}`)
    ElMessage.success('已移除')
    fetchClassStudents(currentClass.value.id)
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '移除失败') }
  finally { classStudentLoading.value = false }
}

const weekdayText = (d: number) => ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][d] || ''

// Tab 切换时加载数据
watch(activeTab, (tab) => {
  if (tab === 'classes') fetchClasses()
  else if (tab === 'courses') fetchCourses()
  else if (tab === 'schedules') { fetchCourses().then(() => fetchSchedules()) }
  else if (tab === 'holidays') fetchHolidays()
})

onMounted(() => fetchClasses())
</script>

<style scoped>
.tab-header {
  display: flex;
  align-items: center;
}
</style>
