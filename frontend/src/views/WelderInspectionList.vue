<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="焊机编号/操作人/备注"
        clearable
        style="width: 220px"
        @keyup.enter="loadData"
      />
      <el-select
        v-model="welderFilter"
        placeholder="焊机"
        clearable
        filterable
        style="width: 180px"
        @change="loadData"
      >
        <el-option
          v-for="item in welders"
          :key="item.id"
          :label="`${item.welder_no}（${item.welder_code}）`"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="faultFilter"
        placeholder="设备状态"
        clearable
        style="width: 140px"
        @change="loadData"
      >
        <el-option label="故障" :value="true" />
        <el-option label="正常" :value="false" />
      </el-select>
      <el-date-picker
        v-model="monthFilter"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        clearable
        @change="loadData"
      />
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        新增巡检单
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
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="welder_no" label="焊机编号" width="110" />
      <el-table-column prop="project_name" label="项目" min-width="120">
        <template #default="{ row }">
          {{ row.project_name || '-' }}
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
      <el-table-column label="日期" width="140">
        <template #default="{ row }">
          {{ formatDateTime(row.inspection_date) }}
        </template>
      </el-table-column>
      <el-table-column prop="inspection_type" label="巡检类型" width="90">
        <template #default="{ row }">
          {{ typeLabel(row.inspection_type) }}
        </template>
      </el-table-column>
      <el-table-column prop="completed" label="是否完成" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.completed ? 'success' : 'info'">
            {{ row.completed ? '完成' : '未完成' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="设备状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.device_status === 'FAULT' ? 'danger' : 'success'">
            {{ row.device_status === 'FAULT' ? '故障' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <AttachmentPreview :url="row.attachment_url" />
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="130" show-overflow-tooltip />
      <el-table-column prop="repair_note" label="维修说明" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.repair_note || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="canEdit && row.device_status === 'FAULT'"
            type="warning"
            link
            size="small"
            @click="openRepair(row)"
          >
            维修说明
          </el-button>
          <el-button v-if="canEdit" type="primary" link size="small" @click="editRow(row)">
            编辑
          </el-button>
          <el-button v-if="isAdmin" type="danger" link size="small" @click="deleteRow(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="680px" @closed="resetForm">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="焊机" prop="welder_id">
              <el-select v-model="formData.welder_id" filterable style="width: 100%" @change="handleWelderChange">
                <el-option
                  v-for="item in welders"
                  :key="item.id"
                  :label="`${item.welder_no}（${item.welder_code}）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所在地">
              <el-input v-model="formData.location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="日期" prop="inspection_date">
              <el-date-picker
                v-model="formData.inspection_date"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="巡检类型" prop="inspection_type">
              <el-select v-model="formData.inspection_type" style="width: 100%">
                <el-option label="月检" value="MONTHLY" />
                <el-option label="周检" value="WEEKLY" />
                <el-option label="日检" value="DAILY" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否完成">
              <el-switch v-model="formData.completed" active-text="完成" inactive-text="未完成" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备状态" prop="device_status">
              <el-select v-model="formData.device_status" style="width: 100%">
                <el-option label="正常" value="NORMAL" />
                <el-option label="故障" value="FAULT" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="操作人">
              <el-input v-model="formData.operator_name" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="附件">
              <PhotoUpload v-model="formData.attachment_url" :max="10" />
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

    <el-dialog v-model="repairVisible" title="维修说明" width="480px">
      <el-form ref="repairFormRef" :model="repairForm" :rules="repairRules" label-width="90px">
        <el-form-item label="维修说明" prop="repair_note">
          <el-input v-model="repairForm.repair_note" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRepair">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import request from '../api/request'
import AttachmentPreview from '../components/AttachmentPreview.vue'
import PhotoUpload from '../components/PhotoUpload.vue'

let userInfo = {}
try {
  userInfo = JSON.parse(
    localStorage.getItem('userInfo') || localStorage.getItem('user') || '{}'
  )
} catch (error) {
  userInfo = {}
}
const isAdmin = userInfo.role === 'ADMIN'
const canEdit = ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'].includes(userInfo.role)

const rows = ref([])
const selectedRows = ref([])
const welders = ref([])
const keyword = ref('')
const welderFilter = ref(null)
const faultFilter = ref(null)
const monthFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增巡检单')
const formRef = ref()
const repairVisible = ref(false)
const repairFormRef = ref()
const repairRecordId = ref(null)

const formData = reactive({
  id: null,
  welder_id: null,
  location: '',
  inspection_date: '',
  inspection_type: 'MONTHLY',
  completed: false,
  attachment_url: '',
  operator_name: '',
  device_status: 'NORMAL',
  remark: '',
})

const formRules = {
  welder_id: [{ required: true, message: '请选择焊机', trigger: 'change' }],
  inspection_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  inspection_type: [{ required: true, message: '请选择巡检类型', trigger: 'change' }],
  device_status: [{ required: true, message: '请选择设备状态', trigger: 'change' }],
}

const repairForm = reactive({ repair_note: '' })
const repairRules = {
  repair_note: [{ required: true, message: '请输入维修说明', trigger: 'blur' }],
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

function typeLabel(type) {
  const map = { MONTHLY: '月检', WEEKLY: '周检', DAILY: '日检' }
  return map[type] || type
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16)
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function nowText() {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}

async function loadWelders() {
  try {
    const res = await request.get('/welders')
    const data = unwrap(res)
    welders.value = Array.isArray(data) ? data : []
  } catch (error) {
    welders.value = []
  }
}

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const res = await request.get('/welder-inspections', {
      params: {
        welder_id: welderFilter.value || undefined,
        keyword: keyword.value || undefined,
        fault: faultFilter.value === null ? undefined : faultFilter.value,
        month: monthFilter.value || undefined,
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

function handleWelderChange(id) {
  const welder = welders.value.find((item) => item.id === id)
  if (welder) {
    formData.location = welder.location || ''
    if (!formData.operator_name) {
      formData.operator_name = welder.welder_manager || ''
    }
  }
}

function resetForm() {
  Object.assign(formData, {
    id: null,
    welder_id: null,
    location: '',
    inspection_date: nowText(),
    inspection_type: 'MONTHLY',
    completed: false,
    attachment_url: '',
    operator_name: userInfo.real_name || '',
    device_status: 'NORMAL',
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增巡检单'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑巡检单'
  Object.assign(formData, {
    id: row.id,
    welder_id: row.welder_id,
    location: row.location || '',
    inspection_date: row.inspection_date,
    inspection_type: row.inspection_type,
    completed: Boolean(row.completed),
    attachment_url: row.attachment_url || '',
    operator_name: row.operator_name || '',
    device_status: row.device_status,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      welder_id: formData.welder_id,
      location: formData.location || null,
      inspection_date: formData.inspection_date,
      inspection_type: formData.inspection_type,
      completed: formData.completed,
      attachment_url: formData.attachment_url || null,
      operator_name: formData.operator_name || null,
      device_status: formData.device_status,
      remark: formData.remark || null,
    }
    if (formData.id) {
      await request.put(`/welder-inspections/${formData.id}`, payload)
      ElMessage.success('巡检单修改成功')
    } else {
      await request.post('/welder-inspections', payload)
      ElMessage.success('巡检单创建成功')
    }
    dialogVisible.value = false
    await Promise.all([loadData(), loadWelders()])
  } catch (error) {
    console.error('保存巡检单失败：', error)
  } finally {
    saving.value = false
  }
}

function openRepair(row) {
  repairRecordId.value = row.id
  repairForm.repair_note = ''
  repairVisible.value = true
}

async function submitRepair() {
  await repairFormRef.value.validate()
  saving.value = true
  try {
    const res = await request.post(
      `/welder-inspections/${repairRecordId.value}/repair`,
      { repair_note: repairForm.repair_note }
    )
    ElMessage.success('维修说明已提交，故障状态已解除')
    repairVisible.value = false
    await Promise.all([loadData(), loadWelders()])
  } catch (error) {
    console.error('提交维修说明失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(`确认删除巡检单 ${row.welder_no}？`, '提示', {
      type: 'warning',
    })
    const res = await request.delete(`/welder-inspections/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除巡检单失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 条巡检单？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/welder-inspections/batch-delete', {
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

onMounted(() => {
  loadWelders()
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

</style>
