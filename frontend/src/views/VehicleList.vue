<template>
  <div class="page">
    <div class="filter-bar">
      <el-input
        v-model="keyword"
        placeholder="车牌号 / 车辆编码"
        clearable
        style="width: 220px"
        @input="handleSearch"
      />
      <el-select
        v-model="statusFilter"
        placeholder="车辆状态"
        clearable
        style="width: 150px"
        @change="handleSearch"
      >
        <el-option
          v-for="item in statusOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-select
        v-model="projectFilter"
        placeholder="所属项目"
        clearable
        filterable
        style="width: 180px"
        @change="handleSearch"
      >
        <el-option
          v-for="item in projectOptions"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>

      <div class="actions">
        <el-button type="primary" :icon="Plus" @click="openAddDialog">
          新增车辆
        </el-button>
        <el-button :icon="Upload" :loading="importing" @click="fileInput?.click()">
          导入 Excel
        </el-button>
        <el-button :icon="Download" :loading="exporting" @click="handleExport">
          导出 Excel
        </el-button>
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx"
          hidden
          @change="handleImport"
        />
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="displayData"
      border
      stripe
      class="data-table"
    >
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="vehicle_code" label="车辆编码" width="110" />
      <el-table-column prop="plate_no" label="车牌号" width="110" />
      <el-table-column prop="project_name" label="所属项目" min-width="120">
        <template #default="{ row }">
          {{ row.project_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="project_manager" label="项目经理" width="100" />
      <el-table-column prop="vehicle_manager" label="车管员" width="100" />
      <el-table-column prop="ownership" label="所有权" width="110">
        <template #default="{ row }">
          {{ ownershipLabel(row.ownership) }}
        </template>
      </el-table-column>
      <el-table-column prop="initial_mileage" label="初始里程" width="100" />
      <el-table-column prop="current_mileage" label="当前里程" width="100" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="vehicle_age" label="车龄(年)" width="80" />
      <el-table-column prop="violation_info" label="违章信息" min-width="120" show-overflow-tooltip />
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" :icon="Edit" @click="editVehicle(row)">
            编辑
          </el-button>
          <el-button type="danger" link size="small" :icon="Delete" @click="deleteVehicle(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper">
      <el-pagination
        v-model:page-size="pageSize"
        v-model:current-page="currentPage"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageChange"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车牌号" prop="plate_no">
              <el-input v-model="formData.plate_no" placeholder="例如：赣A12345" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属项目">
              <el-select v-model="formData.project_id" clearable filterable style="width: 100%">
                <el-option
                  v-for="item in projectOptions"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目经理">
              <el-input v-model="formData.project_manager" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车管员">
              <el-input v-model="formData.vehicle_manager" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所有权">
              <el-select v-model="formData.ownership" style="width: 100%">
                <el-option
                  v-for="item in ownershipOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车辆状态">
              <el-select v-model="formData.status" style="width: 100%">
                <el-option
                  v-for="item in statusOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="初始里程" prop="initial_mileage">
              <el-input-number
                v-model="formData.initial_mileage"
                :min="0"
                :disabled="Boolean(formData.id)"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车龄(年)">
              <el-input-number
                v-model="formData.vehicle_age"
                :min="0"
                :max="50"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="违章信息">
              <el-input
                v-model="formData.violation_info"
                type="textarea"
                :rows="2"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input
                v-model="formData.remark"
                type="textarea"
                :rows="2"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Edit, Plus, Upload } from '@element-plus/icons-vue'
import request from '../api/request'

const keyword = ref('')
const statusFilter = ref('')
const projectFilter = ref(null)
const tableData = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

const importing = ref(false)
const exporting = ref(false)
const fileInput = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('新增车辆')
const submitLoading = ref(false)
const formRef = ref()

const statusOptions = [
  { value: 'ACTIVE', label: '启用' },
  { value: 'MAINTENANCE', label: '维保中' },
  { value: 'DISABLED', label: '已停用' },
  { value: 'RETURNED', label: '已归还' },
]

const ownershipOptions = [
  { value: 'COMPANY', label: '公司车辆' },
  { value: 'RENTAL', label: '租赁车辆' },
  { value: 'TEMPORARY', label: '临时车辆' },
  { value: 'OTHER', label: '其他' },
]

const projectOptions = ref([])

const formData = reactive({
  id: null,
  plate_no: '',
  project_id: null,
  project_manager: '',
  vehicle_manager: '',
  ownership: 'COMPANY',
  initial_mileage: 0,
  status: 'ACTIVE',
  vehicle_age: null,
  violation_info: '',
  remark: '',
})

const formRules = {
  plate_no: [{ required: true, message: '请输入车牌号', trigger: 'blur' }],
  initial_mileage: [{ required: true, message: '请输入初始里程', trigger: 'change' }],
}

const total = computed(() => tableData.value.length)

const displayData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return tableData.value.slice(start, start + pageSize.value)
})

function statusLabel(status) {
  const map = {
    ACTIVE: '启用',
    MAINTENANCE: '维保中',
    DISABLED: '已停用',
    RETURNED: '已归还',
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    ACTIVE: 'success',
    MAINTENANCE: 'warning',
    DISABLED: 'danger',
    RETURNED: 'info',
  }
  return map[status] || ''
}

function ownershipLabel(ownership) {
  const map = {
    COMPANY: '公司车辆',
    RENTAL: '租赁车辆',
    TEMPORARY: '临时车辆',
    OTHER: '其他',
  }
  return map[ownership] || ownership
}

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/vehicles', {
      params: {
        keyword: keyword.value || undefined,
        project_id: projectFilter.value || undefined,
        status: statusFilter.value || undefined,
      },
    })
    const payload = res.data?.data || res.data || []
    tableData.value = Array.isArray(payload) ? payload : []
  } catch (error) {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function loadProjects() {
  try {
    const res = await request.get('/projects')
    const payload = res.data?.data || res.data || []
    projectOptions.value = Array.isArray(payload) ? payload : []
  } catch (error) {
    projectOptions.value = []
  }
}

function handleSearch() {
  currentPage.value = 1
  loadData()
}

function handlePageChange() {
  loadData()
}

function resetForm() {
  formData.id = null
  formData.plate_no = ''
  formData.project_id = null
  formData.project_manager = ''
  formData.vehicle_manager = ''
  formData.ownership = 'COMPANY'
  formData.initial_mileage = 0
  formData.status = 'ACTIVE'
  formData.vehicle_age = null
  formData.violation_info = ''
  formData.remark = ''
}

function openAddDialog() {
  dialogTitle.value = '新增车辆'
  resetForm()
  dialogVisible.value = true
}

function editVehicle(row) {
  dialogTitle.value = '编辑车辆'
  Object.assign(formData, {
    id: row.id,
    plate_no: row.plate_no,
    project_id: row.project_id,
    project_manager: row.project_manager || '',
    vehicle_manager: row.vehicle_manager || '',
    ownership: row.ownership || 'COMPANY',
    initial_mileage: Number(row.initial_mileage || 0),
    status: row.status,
    vehicle_age: row.vehicle_age,
    violation_info: row.violation_info || '',
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  submitLoading.value = true
  try {
    const payload = {
      plate_no: formData.plate_no,
      project_id: formData.project_id,
      project_manager: formData.project_manager || null,
      vehicle_manager: formData.vehicle_manager || null,
      ownership: formData.ownership,
      initial_mileage: Number(formData.initial_mileage || 0),
      status: formData.status,
      vehicle_age: formData.vehicle_age,
      violation_info: formData.violation_info || null,
      remark: formData.remark || null,
    }

    if (formData.id) {
      await request.put(`/vehicles/${formData.id}`, payload)
    } else {
      await request.post('/vehicles', payload)
    }

    ElMessage.success(formData.id ? '车辆修改成功' : '车辆创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存车辆失败：', error)
  } finally {
    submitLoading.value = false
  }
}

async function deleteVehicle(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除车辆 ${row.plate_no}？其里程、维保、报销记录将一并删除，且不可恢复。`,
      '提示',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const res = await request.delete(`/vehicles/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除车辆失败：', error)
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
    const payload = res.data?.data || res.data || {}
    ElMessage.success(payload.message || '导入完成')
    await Promise.all([loadData(), loadProjects()])
  } catch (error) {
    console.error('导入失败：', error)
  } finally {
    importing.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const res = await request.get('/excel/export', {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `车辆里程维保报销台账-${new Date().toISOString().slice(0, 10)}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('导出失败：', error)
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadData()
  loadProjects()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.data-table {
  margin-top: 16px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
