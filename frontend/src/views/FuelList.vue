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
      <el-date-picker
        v-model="monthFilter"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        clearable
        @change="loadData"
      />
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        新增油费
      </el-button>
      <div class="summary">
        共 {{ rows.length }} 条，加油 {{ totalLiters.toFixed(2) }} 升，金额 ¥ {{ totalAmount.toFixed(2) }}
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe class="data-table">
      <el-table-column prop="fuel_date" label="加油日期" width="110" />
      <el-table-column prop="plate_no" label="车牌号" width="120" />
      <el-table-column prop="liters" label="加油量(升)" width="110" />
      <el-table-column prop="unit_price" label="单价(元/升)" width="110" />
      <el-table-column prop="total_amount" label="金额(元)" width="110" />
      <el-table-column prop="mileage" label="里程(km)" width="100">
        <template #default="{ row }">
          {{ row.mileage ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="station" label="加油站" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.station || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="invoice_no" label="发票号" width="130">
        <template #default="{ row }">
          {{ row.invoice_no || '-' }}
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
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px">
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
            <el-form-item label="加油日期" prop="fuel_date">
              <el-date-picker
                v-model="formData.fuel_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="加油量(升)" prop="liters">
              <el-input-number
                v-model="formData.liters"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单价(元/升)" prop="unit_price">
              <el-input-number
                v-model="formData.unit_price"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="金额(元)">
              <el-input-number
                v-model="formData.total_amount"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
              <div class="auto-tip">
                未填写时按 {{ autoTotal.toFixed(2) }} 元计算
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="里程(km)">
              <el-input-number
                v-model="formData.mileage"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="加油站">
              <el-input v-model="formData.station" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发票号">
              <el-input v-model="formData.invoice_no" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="油费附件">
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
const monthFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const attachmentInput = ref()
const dialogVisible = ref(false)
const dialogTitle = ref('新增油费')
const formRef = ref()

const formData = reactive({
  id: null,
  vehicle_id: null,
  fuel_date: '',
  liters: 0,
  unit_price: 0,
  total_amount: 0,
  mileage: null,
  station: '',
  invoice_no: '',
  attachment_url: null,
  remark: '',
})

const formRules = {
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  fuel_date: [{ required: true, message: '请选择加油日期', trigger: 'change' }],
  liters: [{ required: true, message: '请输入加油量', trigger: 'change' }],
  unit_price: [{ required: true, message: '请输入单价', trigger: 'change' }],
}

const autoTotal = computed(
  () => Number(formData.liters || 0) * Number(formData.unit_price || 0)
)
const totalLiters = computed(
  () => rows.value.reduce((sum, row) => sum + Number(row.liters || 0), 0)
)
const totalAmount = computed(
  () => rows.value.reduce((sum, row) => sum + Number(row.total_amount || 0), 0)
)

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

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/fuels', {
      params: {
        vehicle_id: vehicleFilter.value || undefined,
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

function resetForm() {
  Object.assign(formData, {
    id: null,
    vehicle_id: null,
    fuel_date: '',
    liters: 0,
    unit_price: 0,
    total_amount: 0,
    mileage: null,
    station: '',
    invoice_no: '',
    attachment_url: null,
    remark: '',
  })
}

function openAddDialog() {
  dialogTitle.value = '新增油费'
  resetForm()
  dialogVisible.value = true
}

function editRow(row) {
  dialogTitle.value = '编辑油费'
  Object.assign(formData, {
    id: row.id,
    vehicle_id: row.vehicle_id,
    fuel_date: row.fuel_date,
    liters: Number(row.liters || 0),
    unit_price: Number(row.unit_price || 0),
    total_amount: Number(row.total_amount || 0),
    mileage: row.mileage,
    station: row.station || '',
    invoice_no: row.invoice_no || '',
    attachment_url: row.attachment_url || null,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const total = Number(formData.total_amount || 0)
    const payload = {
      vehicle_id: formData.vehicle_id,
      fuel_date: formData.fuel_date,
      liters: formData.liters,
      unit_price: formData.unit_price,
      total_amount: total > 0 ? total : autoTotal.value,
      mileage: formData.mileage,
      station: formData.station || null,
      invoice_no: formData.invoice_no || null,
      attachment_url: formData.attachment_url,
      remark: formData.remark || null,
    }

    if (formData.id) {
      await request.put(`/fuels/${formData.id}`, payload)
      ElMessage.success('油费记录修改成功')
    } else {
      await request.post('/fuels', payload)
      ElMessage.success('油费记录保存成功')
    }

    dialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('保存油费失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.plate_no} 的油费记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/fuels/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除油费记录失败：', error)
    }
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

.auto-tip {
  color: #999;
  font-size: 12px;
  line-height: 1.4;
  margin-top: 4px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
