<template>
  <div class="user-management-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>👥 用户管理</span>
          <el-button type="primary" icon="Plus" @click="openCreateDialog" size="small">新增用户</el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用户名/真实姓名"
          clearable
          style="width: 240px"
          @keyup.enter="fetchUsers(true)"
        />
        <el-select v-model="filters.role" placeholder="角色筛选" clearable style="width: 140px">
          <el-option label="学生" value="student" />
          <el-option label="教师" value="teacher" />
          <el-option label="管理员" value="admin" />
        </el-select>
        <el-select v-model="filters.is_active" placeholder="状态筛选" clearable style="width: 140px">
          <el-option label="启用" value="1" />
          <el-option label="禁用" value="0" />
        </el-select>
        <el-button type="primary" @click="fetchUsers(true)">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table :data="userList" v-loading="isLoading" stripe border style="width: 100%">
        <el-table-column
          type="index"
          label="序号"
          width="70"
          align="center"
          :index="(index: number) => (pagination.page - 1) * pagination.page_size + index + 1"
        />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="real_name" label="真实姓名" width="150" />
        <el-table-column label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="200">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm
              title="确定要删除该用户吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button type="danger" size="small" icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          background
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="fetchUsers()"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 新增 / 编辑 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="450px">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="用户名" v-if="!isEdit">
          <el-input v-model="formData.username" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="密码" v-if="!isEdit">
          <el-input v-model="formData.password" type="password" placeholder="初始密码" show-password />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="formData.real_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="formData.role" placeholder="选择角色" style="width: 100%">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="isEdit">
          <el-switch v-model="formData.is_active" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const userList = ref<any[]>([])
const isLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)

const filters = reactive({
  keyword: '',
  role: '',
  is_active: '',
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
})

const formData = reactive({
  username: '',
  password: '',
  real_name: '',
  role: 'student',
  is_active: 1,
})

const fetchUsers = async (resetPage = false) => {
  if (resetPage) pagination.page = 1
  isLoading.value = true
  try {
    const res = await request.get('/api/v1/users/page', {
      params: {
        page: pagination.page,
        page_size: pagination.page_size,
        keyword: filters.keyword || undefined,
        role: filters.role || undefined,
        is_active: filters.is_active === '' ? undefined : Number(filters.is_active),
      },
    })
    userList.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch {
    ElMessage.error('获取用户列表失败')
  } finally {
    isLoading.value = false
  }
}

const onPageSizeChange = () => {
  pagination.page = 1
  fetchUsers()
}

const resetFilters = () => {
  filters.keyword = ''
  filters.role = ''
  filters.is_active = ''
  fetchUsers(true)
}

const openCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  formData.username = ''
  formData.password = ''
  formData.real_name = ''
  formData.role = 'student'
  formData.is_active = 1
  dialogVisible.value = true
}

const openEditDialog = (row: any) => {
  isEdit.value = true
  editingId.value = row.id
  formData.real_name = row.real_name
  formData.role = row.role
  formData.is_active = row.is_active
  dialogVisible.value = true
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    if (isEdit.value && editingId.value) {
      await request.put(`/api/v1/users/${editingId.value}`, {
        real_name: formData.real_name,
        role: formData.role,
        is_active: formData.is_active,
      })
      ElMessage.success('用户信息已更新')
    } else {
      if (!formData.username || !formData.password || !formData.real_name) {
        ElMessage.warning('请填写完整信息')
        submitting.value = false
        return
      }
      await request.post('/api/v1/users', {
        username: formData.username,
        password: formData.password,
        real_name: formData.real_name,
        role: formData.role,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await request.delete(`/api/v1/users/${id}`)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

const roleText = (r: string) => ({ student: '学生', teacher: '教师', admin: '管理员' }[r] || r)
const roleTagType = (r: string) => ({ student: '', teacher: 'warning', admin: 'danger' }[r] || '')

onMounted(() => fetchUsers())
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.pagination-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
