<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="编码/编号/地点/负责人"
        clearable
        style="width: 220px"
        @keyup.enter="loadData"
      />
      <el-select
        v-model="projectFilter"
        placeholder="所属项目"
        clearable
        filterable
        style="width: 180px"
        @change="loadData"
      >
        <el-option
          v-for="item in projects"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="projectManagerFilter"
        placeholder="项目负责人"
        clearable
        filterable
        style="width: 160px"
        @change="loadData"
      >
        <el-option
          v-for="item in projectManagerOptions"
          :key="item"
          :label="item"
          :value="item"
        />
      </el-select>
      <el-select
        v-model="statusFilter"
        placeholder="状态"
        clearable
        style="width: 130px"
        @change="loadData"
      >
        <el-option label="在线" value="ONLINE" />
        <el-option label="离线" value="OFFLINE" />
        <el-option label="故障" value="FAULT" />
      </el-select>
      <el-button v-if="canManage" type="primary" :icon="Plus" @click="openAddDialog">
        新增焊机
      </el-button>
      <a
        class="el-button export-link"
        :href="welderExportUrl"
        :download="`焊机台账-${today}.xlsx`"
      >
        <el-icon style="margin-right: 4px"><Download /></el-icon>
        导出 Excel
      </a>
      <el-button v-if="canManage" :icon="Upload" :loading="importing" @click="fileInput?.click()">
        导入 Excel
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
      <input ref="fileInput" type="file" accept=".xlsx" hidden @change="handleImport" />
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
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="welder_code" label="焊机编码" width="110" />
      <el-table-column prop="welder_no" label="焊机编号" width="110" />
      <el-table-column prop="location" label="所在地" min-width="120" />
      <el-table-column prop="project_name" label="所属项目" min-width="130">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.project_enabled ? 'success' : 'danger'"
          >
            {{ row.project_name || '未关联项目' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="project_manager" label="项目负责人" width="110">
        <template #default="{ row }">
          {{ row.project_manager || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="welder_manager" label="焊机负责人" width="110">
        <template #default="{ row }">
          {{ row.welder_manager || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTagType(row.status)">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canManage" type="primary" link size="small" :icon="Edit" @click="editRow(row)">
            编辑
          </el-button>
          <el-button v-if="isAdmin" type="danger" link size="small" :icon="Delete" @click="deleteRow(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" @closed="resetForm">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="焊机编码" prop="welder_code">
              <el-input
                v-model="formData.welder_code"
                disabled
                :placeholder="formData.id ? '' : '自动生成'"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="焊机编号" prop="welder_no">
              <el-input v-model="formData.welder_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所在地">
              <el-input v-model="formData.location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属项目">
              <el-select
                v-model="formData.project_id"
                clearable
                filterable
                style="width: 100%"
                @change="handleProjectChange"
              >
                <el-option
                  v-for="item in projects"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="焊机负责人">
              <el-input v-model="formData.welder_manager" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="formData.status" style="width: 100%">
                <el-option label="在线" value="ONLINE" />
                <el-option label="离线" value="OFFLINE" />
                <el-option label="故障" value="FAULT" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="formData.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Edit, Plus, Upload } from '@element-plus/icons-vue'
import request from '../api/request'

let userInfo = {}
try {
  userInfo = JSON.parse(
    localStorage.getItem('userInfo') || localStorage.getItem('user') || '{}'
  )
} catch (error) {
  userInfo = {}
}
const isAdmin = userInfo.role === 'ADMIN'
const canManage = ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER'].includes(userInfo.role)

const rows = ref([])
const selectedRows = ref([])
const projects = ref([])
const keyword = ref('')
const projectFilter = ref(null)
const projectManagerFilter = ref('')
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const fileInput = ref()
const today = new Date().toISOString().slice(0, 10)
const welderExportUrl = computed(() => {
  const token = localStorage.getItem('token') || ''
  return `/api/excel/export/welders?token=${encodeURIComponent(token)}`
})
const projectManagerOptions = computed(() => {
  const names = projects.value
    .map((item) => item.manager_name)
    .filter(Boolean)
  return [...new Set(names)]
})
const dialogVisible = ref(false)
const dialogTitle = ref('新增焊机')
const formRef = ref()

const formData = reactive({
  id: null,
  welder_code: '',
  welder_no: '',
  location: '',
  project_id: null,
  welder_manager: '',
  status: 'ONLINE',
  remark: '',
})

const formRules = {
  welder_no: [{ required: true, message: '请输入焊机编号', trigger: 'blur' }],
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

function handleProjectChange(projectId) {
  const project = projects.value.find((item) => item.id === projectId)
  if (project) {
    formData.location = project.location || ''
  }
}

function statusLabel(status) {
  const map = { ONLINE: '在线', OFFLINE: '离线', FAULT: '故障' }
  return map[status] || status
}

function statusTagType(status) {
  const map = { ONLINE: 'success', OFFLINE: 'info', FAULT: 'danger' }
  return map[status] || ''
}

async function loadProjects() {
  try {
    const res = await request.get('/projects')
    const data = unwrap(res)
    projects.value = Array.isArray(data) ? data : []
  } catch (error) {
    projects.value = []
  }
}

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const res = await request.get('/welders', {
      params: {
        keyword: keyword.value || undefined,
        project_id: projectFilter.value || undefined,
        project_manager: projectManagerFilter.value || undefined,
        status: statusFilter.value || undefined,
      },
    })
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
    welder_code: '',
    welder_no: '',
    location: '',
    project_id: null,
    welder_manager: '',
    status: 'ONLINE',
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增焊机'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑焊机'
  Object.assign(formData, {
    id: row.id,
    welder_code: row.welder_code,
    welder_no: row.welder_no,
    location: row.location || '',
    project_id: row.project_id,
    welder_manager: row.welder_manager || '',
    status: row.status,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      welder_code: formData.welder_code,
      welder_no: formData.welder_no,
      location: formData.location || null,
      project_id: formData.project_id,
      welder_manager: formData.welder_manager || null,
      status: formData.status,
      remark: formData.remark || null,
    }
    if (formData.id) {
      await request.put(`/welders/${formData.id}`, payload)
      ElMessage.success('焊机修改成功')
    } else {
      await request.post('/welders', payload)
      ElMessage.success('焊机创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存焊机失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(`确认删除焊机 ${row.welder_no}？`, '提示', {
      type: 'warning',
    })
    const res = await request.delete(`/welders/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除焊机失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 台焊机？相关巡检记录将一并删除。`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/welders/batch-delete', {
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

async function handleImport(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  importing.value = true
  try {
    const res = await request.post('/excel/import', formData)
    const payload = unwrap(res)
    ElMessage.success(payload.message || '导入完成')
    await loadData()
  } catch (error) {
    console.error('导入失败：', error)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadProjects()
  loadData()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.data-table {
  margin-top: 16px;
}

.export-link,
.export-link:hover {
  text-decoration: none;
}

</style>
