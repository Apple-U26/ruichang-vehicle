<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        新增用户
      </el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe class="data-table">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="real_name" label="姓名" width="140" />
      <el-table-column prop="role" label="角色" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="roleTagType(row.role)">
            {{ roleLabel(row.role) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="绑定车辆" width="150">
        <template #default="{ row }">
          {{ row.plate_no || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" :icon="Edit" @click="editRow(row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formData.username"
            :disabled="Boolean(formData.id)"
            placeholder="登录账号"
          />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="formData.real_name" />
        </el-form-item>
        <el-form-item :label="formData.id ? '重置密码' : '初始密码'" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            show-password
            :placeholder="formData.id ? '留空则不修改' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" style="width: 100%">
            <el-option
              v-for="item in roleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="formData.role === 'DRIVER'"
          label="绑定车辆"
        >
          <el-select
            v-model="formData.vehicle_id"
            clearable
            filterable
            placeholder="请选择车辆"
            style="width: 100%"
          >
            <el-option
              v-for="item in vehicles"
              :key="item.id"
              :label="`${item.plate_no}（${item.vehicle_code}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Plus } from '@element-plus/icons-vue'
import request from '../api/request'

const rows = ref([])
const vehicles = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增用户')
const formRef = ref()

const roleOptions = [
  { value: 'ADMIN', label: '系统管理员' },
  { value: 'VEHICLE_MANAGER', label: '车辆管理员' },
  { value: 'PROJECT_MANAGER', label: '项目经理' },
  { value: 'FINANCE', label: '财务人员' },
  { value: 'DRIVER', label: '驾驶员' },
]

const formData = reactive({
  id: null,
  username: '',
  real_name: '',
  password: '',
  role: 'DRIVER',
  enabled: true,
  vehicle_id: null,
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少 2 位', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!formData.id && (!value || value.length < 6)) {
          callback(new Error('初始密码至少 6 位'))
        } else if (formData.id && value && value.length < 6) {
          callback(new Error('重置密码至少 6 位'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

async function loadVehicles() {
  try {
    const res = await request.get('/vehicles')
    const data = unwrap(res)
    vehicles.value = Array.isArray(data) ? data : []
  } catch (error) {
    vehicles.value = []
  }
}

function roleLabel(role) {
  const map = {
    ADMIN: '系统管理员',
    VEHICLE_MANAGER: '车辆管理员',
    PROJECT_MANAGER: '项目经理',
    FINANCE: '财务人员',
    DRIVER: '驾驶员',
  }
  return map[role] || role
}

function roleTagType(role) {
  const map = {
    ADMIN: 'danger',
    VEHICLE_MANAGER: 'warning',
    PROJECT_MANAGER: 'primary',
    FINANCE: 'success',
    DRIVER: 'info',
  }
  return map[role] || ''
}

function formatDate(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/users')
    const data = unwrap(res)
    rows.value = Array.isArray(data) ? data : []
  } catch (error) {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(formData, {
    id: null,
    username: '',
    real_name: '',
    password: '',
    role: 'DRIVER',
    enabled: true,
    vehicle_id: null,
  })
}

function openAddDialog() {
  dialogTitle.value = '新增用户'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑用户'
  Object.assign(formData, {
    id: row.id,
    username: row.username,
    real_name: row.real_name,
    password: '',
    role: row.role,
    enabled: Boolean(row.enabled),
    vehicle_id: row.vehicle_id,
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (formData.id) {
      await request.put(`/users/${formData.id}`, {
        real_name: formData.real_name,
        role: formData.role,
        enabled: formData.enabled,
        password: formData.password || null,
        vehicle_id:
          formData.role === 'DRIVER' ? formData.vehicle_id : null,
      })
      ElMessage.success('用户修改成功')
    } else {
      await request.post('/users', {
        username: formData.username,
        real_name: formData.real_name,
        password: formData.password,
        role: formData.role,
        enabled: formData.enabled,
        vehicle_id:
          formData.role === 'DRIVER' ? formData.vehicle_id : null,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存用户失败：', error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadData()
  loadVehicles()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
}

.data-table {
  margin-top: 16px;
}
</style>
