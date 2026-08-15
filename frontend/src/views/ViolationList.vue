<template>
  <div class="page">
    <div class="toolbar">
      <el-select
        v-model="vehicleFilter"
        placeholder="全部车辆"
        clearable
        filterable
        style="width: 210px"
        @change="loadData"
      >
        <el-option
          v-for="item in vehicles"
          :key="item.id"
          :label="`${item.plate_no}（${item.vehicle_code}）`"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="statusFilter"
        placeholder="处理状态"
        clearable
        style="width: 140px"
        @change="loadData"
      >
        <el-option
          v-for="item in statusOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        新增违章
      </el-button>
      <div class="summary">
        未处理 {{ pendingCount }} 条，罚款合计 ¥ {{ totalFine.toFixed(2) }}
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe class="data-table">
      <el-table-column prop="violation_date" label="违章日期" width="110" />
      <el-table-column prop="plate_no" label="车牌号" width="120" />
      <el-table-column prop="violation_type" label="违章类型" min-width="120">
        <template #default="{ row }">
          {{ row.violation_type || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="location" label="违章地点" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.location || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="points" label="扣分" width="80">
        <template #default="{ row }">
          {{ row.points ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="fine_amount" label="罚款(元)" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'PROCESSED' ? 'success' : 'danger'">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <el-link
            v-if="row.attachment_url"
            type="primary"
            :href="row.attachment_url"
            target="_blank"
          >
            查看
          </el-link>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="handler_name" label="处理人" width="100">
        <template #default="{ row }">
          {{ row.handler_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" :icon="Edit" @click="editRow(row)">
            编辑
          </el-button>
          <el-button type="danger" link size="small" :icon="Delete" @click="deleteRow(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="620px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆" prop="vehicle_id">
              <el-select v-model="formData.vehicle_id" filterable style="width: 100%">
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="`${item.plate_no}（${item.vehicle_code}）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="违章日期" prop="violation_date">
              <el-date-picker
                v-model="formData.violation_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="违章类型">
              <el-input v-model="formData.violation_type" placeholder="例如：违停、超速" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="违章地点">
              <el-input v-model="formData.location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="扣分">
              <el-input-number
                v-model="formData.points"
                :min="0"
                :max="12"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="罚款金额">
              <el-input-number
                v-model="formData.fine_amount"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="处理状态">
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
            <el-form-item label="处理人">
              <el-input v-model="formData.handler_name" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="违章附件">
              <div class="upload-row">
                <input
                  ref="attachmentInput"
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  hidden
                  @change="handleAttachment"
                />
                <el-button
                  :icon="Upload"
                  :loading="uploading"
                  @click="attachmentInput?.click()"
                >
                  {{ formData.attachment_url ? '重新上传' : '上传图片' }}
                </el-button>
                <el-link
                  v-if="formData.attachment_url"
                  type="primary"
                  :href="formData.attachment_url"
                  target="_blank"
                >
                  查看
                </el-link>
              </div>
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
        <el-button type="primary" :loading="saving" @click="submitForm">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Upload } from '@element-plus/icons-vue'
import request from '../api/request'

const rows = ref([])
const vehicles = ref([])
const vehicleFilter = ref(null)
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const attachmentInput = ref()
const dialogVisible = ref(false)
const dialogTitle = ref('新增违章')
const formRef = ref()

const statusOptions = [
  { value: 'UNPROCESSED', label: '未处理' },
  { value: 'PROCESSED', label: '已处理' },
]

const formData = reactive({
  id: null,
  vehicle_id: null,
  violation_date: '',
  violation_type: '',
  location: '',
  attachment_url: '',
  points: null,
  fine_amount: 0,
  status: 'UNPROCESSED',
  handler_name: '',
  remark: '',
})

const formRules = {
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  violation_date: [{ required: true, message: '请选择违章日期', trigger: 'change' }],
}

const pendingCount = computed(
  () => rows.value.filter((row) => row.status === 'UNPROCESSED').length
)
const totalFine = computed(
  () => rows.value.reduce((sum, row) => sum + Number(row.fine_amount || 0), 0)
)

function unwrap(res) {
  return res.data?.data || res.data || res
}

function statusLabel(status) {
  const map = {
    UNPROCESSED: '未处理',
    PROCESSED: '已处理',
  }
  return map[status] || status
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

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/violations', {
      params: {
        vehicle_id: vehicleFilter.value || undefined,
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
    vehicle_id: null,
    violation_date: '',
    violation_type: '',
    location: '',
    attachment_url: '',
    points: null,
    fine_amount: 0,
    status: 'UNPROCESSED',
    handler_name: '',
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增违章'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑违章'
  Object.assign(formData, {
    id: row.id,
    vehicle_id: row.vehicle_id,
    violation_date: row.violation_date,
    violation_type: row.violation_type || '',
    location: row.location || '',
    attachment_url: row.attachment_url || '',
    points: row.points,
    fine_amount: Number(row.fine_amount || 0),
    status: row.status,
    handler_name: row.handler_name || '',
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      vehicle_id: formData.vehicle_id,
      violation_date: formData.violation_date,
      violation_type: formData.violation_type || null,
      location: formData.location || null,
      attachment_url: formData.attachment_url || null,
      points: formData.points,
      fine_amount: formData.fine_amount,
      status: formData.status,
      handler_name: formData.handler_name || null,
      remark: formData.remark || null,
    }

    if (formData.id) {
      await request.put(`/violations/${formData.id}`, payload)
      ElMessage.success('违章记录修改成功')
    } else {
      await request.post('/violations', payload)
      ElMessage.success('违章记录保存成功')
    }

    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存违章失败：', error)
  } finally {
    saving.value = false
  }
}

async function handleAttachment(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const uploadData = new FormData()
  uploadData.append('file', file)
  uploading.value = true
  try {
    const res = await request.post('/upload', uploadData)
    const payload = res.data?.data || res.data || {}
    formData.attachment_url = payload.url || ''
    ElMessage.success('附件上传成功')
  } catch (error) {
    console.error('附件上传失败：', error)
  } finally {
    uploading.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.plate_no} 的违章记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/violations/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除违章记录失败：', error)
    }
  }
}

onMounted(() => {
  loadVehicles()
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

.summary {
  margin-left: auto;
  color: #666;
  font-size: 14px;
}

.data-table {
  margin-top: 16px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
