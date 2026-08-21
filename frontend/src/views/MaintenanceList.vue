<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="车牌/项目/服务商"
        clearable
        style="width: 220px"
        @keyup.enter="loadData"
      />
      <el-select
        v-model="vehicleFilter"
        placeholder="全部车辆"
        clearable
        filterable
        style="width: 200px"
        @change="loadData"
      >
        <el-option
          v-for="item in vehicles"
          :key="item.id"
          :label="`${item.plate_no}（${item.vehicle_code}）`"
          :value="item.id"
        />
      </el-select>
      <el-button v-if="!isFinance" type="primary" :icon="Plus" @click="openAddDialog">
        新增维保
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
      <el-table-column prop="maintenance_date" label="维保日期" width="110" />
      <el-table-column prop="plate_no" label="车牌号" width="110" />
      <el-table-column prop="current_mileage" label="当前里程" width="100" />
      <el-table-column prop="maintenance_type" label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTagType(row.maintenance_type)">
            {{ typeLabel(row.maintenance_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="items" label="维保项目" min-width="160" show-overflow-tooltip />
      <el-table-column prop="amount" label="金额(元)" width="100" />
      <el-table-column prop="service_provider" label="服务商" width="130" />
      <el-table-column prop="operator_name" label="操作人" width="100" />
      <el-table-column prop="next_mileage" label="下次里程" width="100">
        <template #default="{ row }">
          {{ row.next_mileage ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="next_date" label="下次日期" width="110">
        <template #default="{ row }">
          {{ row.next_date || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="canEdit"
            type="primary"
            link
            size="small"
            :icon="Edit"
            @click="editRow(row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="isAdmin"
            type="danger"
            link
            size="small"
            :icon="Delete"
            @click="deleteRow(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆" prop="vehicle_id">
              <el-select v-model="formData.vehicle_id" filterable style="width: 100%">
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="`${item.plate_no}（当前 ${item.current_mileage} km）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="维保日期" prop="maintenance_date">
              <el-date-picker
                v-model="formData.maintenance_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前里程" prop="current_mileage">
              <el-input-number
                v-model="formData.current_mileage"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="维保类型" prop="maintenance_type">
              <el-select v-model="formData.maintenance_type" style="width: 100%">
                <el-option
                  v-for="item in typeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="金额(元)" prop="amount">
              <el-input-number
                v-model="formData.amount"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="服务商">
              <el-input v-model="formData.service_provider" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="操作人">
              <el-input v-model="formData.operator_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="下次里程">
              <el-input-number
                v-model="formData.next_mileage"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="下次日期">
              <el-date-picker
                v-model="formData.next_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="维保项目" prop="items">
              <el-input
                v-model="formData.items"
                type="textarea"
                :rows="2"
                placeholder="例如：更换机油、机滤、空滤"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="formData.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="维保照片" required>
              <PhotoUpload v-model="formData.attachment_url" />
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import request from '../api/request'
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
const isFinance = userInfo.role === 'FINANCE'
const canEdit = ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER'].includes(userInfo.role)

const rows = ref([])
const selectedRows = ref([])
const vehicles = ref([])
const vehicleFilter = ref(null)
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增维保')
const formRef = ref()

const typeOptions = [
  { value: 'MAINTENANCE', label: '保养' },
  { value: 'REPAIR', label: '维修' },
  { value: 'INSPECTION', label: '年检' },
  { value: 'INSURANCE', label: '保险' },
]

const formData = reactive({
  id: null,
  vehicle_id: null,
  maintenance_date: '',
  current_mileage: 0,
  maintenance_type: 'MAINTENANCE',
  items: '',
  amount: 0,
  service_provider: '',
  operator_name: '',
  next_mileage: null,
  next_date: null,
  attachment_url: null,
  remark: '',
})

const formRules = {
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  maintenance_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  current_mileage: [{ required: true, message: '请输入当前里程', trigger: 'change' }],
  maintenance_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  items: [{ required: true, message: '请输入维保项目', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'change' }],
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

function typeLabel(type) {
  const map = {
    MAINTENANCE: '保养',
    REPAIR: '维修',
    INSPECTION: '年检',
    INSURANCE: '保险',
  }
  return map[type] || type
}

function typeTagType(type) {
  const map = {
    MAINTENANCE: 'success',
    REPAIR: 'warning',
    INSPECTION: 'info',
    INSURANCE: 'primary',
  }
  return map[type] || ''
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
    selectedRows.value = []
    const res = await request.get('/maintenances', {
      params: {
        vehicle_id: vehicleFilter.value || undefined,
        keyword: keyword.value || undefined,
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
    maintenance_date: '',
    current_mileage: 0,
    maintenance_type: 'MAINTENANCE',
    items: '',
    amount: 0,
    service_provider: '',
    operator_name: '',
    next_mileage: null,
    next_date: null,
    attachment_url: null,
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增维保'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑维保'
  Object.assign(formData, {
    id: row.id,
    vehicle_id: row.vehicle_id,
    maintenance_date: row.maintenance_date,
    current_mileage: Number(row.current_mileage || 0),
    maintenance_type: row.maintenance_type,
    items: row.items,
    amount: Number(row.amount || 0),
    service_provider: row.service_provider || '',
    operator_name: row.operator_name || '',
    next_mileage: row.next_mileage,
    next_date: row.next_date,
    attachment_url: row.attachment_url || null,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  if (!formData.attachment_url) {
    ElMessage.warning('请上传维保照片')
    return
  }
  saving.value = true
  try {
    const payload = {
      vehicle_id: formData.vehicle_id,
      maintenance_date: formData.maintenance_date,
      current_mileage: formData.current_mileage,
      maintenance_type: formData.maintenance_type,
      items: formData.items,
      amount: formData.amount,
      service_provider: formData.service_provider || null,
      operator_name: formData.operator_name || null,
      next_mileage: formData.next_mileage,
      next_date: formData.next_date,
      attachment_url: formData.attachment_url,
      remark: formData.remark || null,
    }

    if (formData.id) {
      await request.put(`/maintenances/${formData.id}`, payload)
      ElMessage.success('维保记录修改成功')
    } else {
      await request.post('/maintenances', payload)
      ElMessage.success('维保记录保存成功')
    }

    dialogVisible.value = false
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    console.error('保存维保失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.plate_no} 的维保记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/maintenances/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除维保记录失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 条维保记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/maintenances/batch-delete', {
      ids: selectedRows.value.map((row) => row.id),
    })
    ElMessage.success(res.data?.message || '批量删除成功')
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败：', error)
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
}

.data-table {
  margin-top: 16px;
}

</style>
