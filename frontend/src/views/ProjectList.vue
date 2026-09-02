<template>
  <div class="page">
    <div class="toolbar">
      <el-button v-if="canManage" type="primary" :icon="Plus" @click="openAddDialog">
        新增项目
      </el-button>
      <el-button
        v-if="isAdmin"
        type="danger"
        :icon="Delete"
        :disabled="!selectedRows.length"
        @click="batchDelete"
      >
        批量删除
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      border
      stripe
      class="data-table"
      @selection-change="selectedRows = $event"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="项目名称" min-width="180" />
      <el-table-column prop="manager_name" label="项目负责人" width="130">
        <template #default="{ row }">
          {{ row.manager_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="location" label="所在地" min-width="140">
        <template #default="{ row }">
          {{ row.location || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canEditRow(row)" type="primary" link size="small" :icon="Edit" @click="editRow(row)">
            编辑
          </el-button>
          <el-button v-if="isAdmin" type="danger" link size="small" :icon="Delete" @click="deleteRow(row)">
            删除
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
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="项目负责人">
          <el-input v-model="formData.manager_name" />
        </el-form-item>
        <el-form-item label="所在地">
          <el-input v-model="formData.location" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.remark" type="textarea" :rows="3" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import request from '../api/request'

let userInfo = {}
try {
  userInfo = JSON.parse(
    localStorage.getItem('userInfo') || localStorage.getItem('user') || '{}'
  )
} catch (error) {
  userInfo = {}
}
const canManage = ['ADMIN', 'PROJECT_MANAGER', 'FINANCE'].includes(userInfo.role)
const isAdmin = userInfo.role === 'ADMIN'
const userRole = userInfo.role
const userRealName = userInfo.real_name || ''

function canEditRow(row) {
  if (userRole === 'ADMIN' || userRole === 'FINANCE') return true
  if (userRole === 'PROJECT_MANAGER') {
    return true
  }
  return false
}

const rows = ref([])
const selectedRows = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增项目')
const formRef = ref()

const formData = reactive({
  id: null,
  name: '',
  manager_name: '',
  location: '',
  enabled: true,
  remark: '',
})

const formRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const res = await request.get('/projects')
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
    name: '',
    manager_name: '',
    location: '',
    enabled: true,
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增项目'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑项目'
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    manager_name: row.manager_name || '',
    location: row.location || '',
    enabled: Boolean(row.enabled),
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      name: formData.name,
      manager_name: formData.manager_name || null,
      location: formData.location || null,
      enabled: formData.enabled,
      remark: formData.remark || null,
    }

    if (formData.id) {
      await request.put(`/projects/${formData.id}`, payload)
      ElMessage.success('项目修改成功')
    } else {
      await request.post('/projects', payload)
      ElMessage.success('项目创建成功')
    }

    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存项目失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除项目 ${row.name}？项目下仍有车辆时将自动停用。`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/projects/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除项目失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 个项目？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/projects/batch-delete', {
      ids: selectedRows.value.map((row) => row.id),
    })
    ElMessage.success(res.data?.message || '批量删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败：', error)
    }
  }
}

onMounted(loadData)
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
