<template>
  <div class="page">
    <div class="toolbar">
      <el-date-picker
        v-model="month"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        clearable
      />
      <el-button type="primary" :icon="Search" @click="loadData">
        查询
      </el-button>
      <el-button type="success" :icon="Plus" @click="openOut">
        出车登记
      </el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe class="data-table">
      <el-table-column prop="trip_date" label="日期" width="110" />
      <el-table-column prop="plate_no" label="车牌号" width="110" />
      <el-table-column prop="driver_name" label="驾驶人" width="100" />
      <el-table-column prop="out_mileage" label="出车里程" width="100" />
      <el-table-column prop="in_mileage" label="收车里程" width="100">
        <template #default="{ row }">
          {{ row.in_mileage ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="distance" label="本次里程" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'CLOSED' ? 'success' : 'warning'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="异常" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.abnormal" type="danger" size="small">
            {{ row.abnormal_reason || '异常' }}
          </el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="用车事由" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'OUT'"
            type="primary"
            link
            size="small"
            @click="openClose(row)"
          >
            收车
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="outVisible" title="出车登记" width="640px">
      <el-form ref="outFormRef" :model="outForm" :rules="outRules" label-width="100px">
        <el-form-item label="车辆" prop="vehicle_id">
          <el-select v-model="outForm.vehicle_id" filterable style="width: 100%">
            <el-option
              v-for="vehicle in vehicles"
              :key="vehicle.id"
              :label="`${vehicle.plate_no}（当前 ${vehicle.current_mileage} km）`"
              :value="vehicle.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="出车日期" prop="trip_date">
          <el-date-picker
            v-model="outForm.trip_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="出车里程" prop="out_mileage">
          <el-input-number
            v-model="outForm.out_mileage"
            :min="0"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="驾驶人">
          <el-input v-model="outForm.driver_name" />
        </el-form-item>
        <el-form-item label="出发地">
          <el-input v-model="outForm.departure" />
        </el-form-item>
        <el-form-item label="目的地">
          <el-input v-model="outForm.destination" />
        </el-form-item>
        <el-form-item label="用车事由">
          <el-input v-model="outForm.purpose" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="出车照片">
          <div class="upload-row">
            <input
              ref="outPhotoInput"
              type="file"
              accept=".jpg,.jpeg,.png,.pdf"
              hidden
              @change="handleOutPhoto"
            />
            <el-button :icon="Upload" :loading="uploading" @click="outPhotoInput?.click()">
              上传照片
            </el-button>
            <el-link v-if="outForm.out_photo" type="primary" :href="outForm.out_photo" target="_blank">
              查看
            </el-link>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="outForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="outVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveOut">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="closeVisible" title="收车登记" width="520px">
      <el-form ref="closeFormRef" :model="closeForm" :rules="closeRules" label-width="110px">
        <el-form-item label="出车里程">
          <el-input :model-value="closeForm.out_mileage" disabled />
        </el-form-item>
        <el-form-item label="收车里程" prop="in_mileage">
          <el-input-number
            v-model="closeForm.in_mileage"
            :min="closeForm.out_mileage"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="收车照片">
          <div class="upload-row">
            <input
              ref="inPhotoInput"
              type="file"
              accept=".jpg,.jpeg,.png,.pdf"
              hidden
              @change="handleInPhoto"
            />
            <el-button :icon="Upload" :loading="uploading" @click="inPhotoInput?.click()">
              上传照片
            </el-button>
            <el-link v-if="closeForm.in_photo" type="primary" :href="closeForm.in_photo" target="_blank">
              查看
            </el-link>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveClose">
          确认收车
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search, Upload } from '@element-plus/icons-vue'
import request from '../api/request'

const rows = ref([])
const vehicles = ref([])
const month = ref('')
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)

const outVisible = ref(false)
const closeVisible = ref(false)
const closeRecordId = ref(null)
const outFormRef = ref()
const closeFormRef = ref()
const outPhotoInput = ref()
const inPhotoInput = ref()

const outForm = reactive({
  vehicle_id: null,
  trip_date: '',
  out_mileage: 0,
  driver_name: '',
  departure: '',
  destination: '',
  purpose: '',
  out_photo: null,
  remark: null,
})

const closeForm = reactive({
  out_mileage: 0,
  in_mileage: 0,
  in_photo: null,
})

const outRules = {
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  trip_date: [{ required: true, message: '请选择出车日期', trigger: 'change' }],
  out_mileage: [{ required: true, message: '请输入出车里程', trigger: 'change' }],
}

const closeRules = {
  in_mileage: [{ required: true, message: '请输入收车里程', trigger: 'change' }],
}

function statusLabel(status) {
  return status === 'OUT' ? '出车中' : status === 'CLOSED' ? '已收车' : status
}

function unwrap(res) {
  return res.data?.data || res.data || res
}

async function loadVehicles() {
  try {
    const res = await request.get('/vehicles', {
      params: { status: 'ACTIVE' },
    })
    const data = unwrap(res)
    vehicles.value = Array.isArray(data) ? data : []
  } catch (error) {
    vehicles.value = []
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/mileages', {
      params: { month: month.value || undefined },
    })
    const data = unwrap(res)
    rows.value = Array.isArray(data) ? data : []
  } catch (error) {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openOut() {
  const today = new Date()
  const dateText = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  Object.assign(outForm, {
    vehicle_id: null,
    trip_date: dateText,
    out_mileage: 0,
    driver_name: '',
    departure: '',
    destination: '',
    purpose: '',
    out_photo: null,
    remark: null,
  })
  outVisible.value = true
}

async function saveOut() {
  await outFormRef.value.validate()
  saving.value = true
  try {
    await request.post('/mileages/out', {
      vehicle_id: outForm.vehicle_id,
      trip_date: outForm.trip_date,
      out_mileage: outForm.out_mileage,
      driver_name: outForm.driver_name || null,
      departure: outForm.departure || null,
      destination: outForm.destination || null,
      purpose: outForm.purpose || null,
      out_photo: outForm.out_photo,
      remark: outForm.remark || null,
    })
    ElMessage.success('出车登记成功')
    outVisible.value = false
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    console.error('出车登记失败：', error)
  } finally {
    saving.value = false
  }
}

function openClose(row) {
  closeRecordId.value = row.id
  closeForm.out_mileage = Number(row.out_mileage || 0)
  closeForm.in_mileage = Number(row.out_mileage || 0)
  closeForm.in_photo = null
  closeVisible.value = true
}

async function saveClose() {
  await closeFormRef.value.validate()
  saving.value = true
  try {
    const res = await request.put(`/mileages/${closeRecordId.value}/close`, {
      in_mileage: closeForm.in_mileage,
      in_photo: closeForm.in_photo,
    })
    const payload = unwrap(res)
    ElMessage.success(
      `收车成功，本次行驶 ${payload.distance ?? 0} 公里`
    )
    closeVisible.value = false
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    console.error('收车失败：', error)
  } finally {
    saving.value = false
  }
}

async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  uploading.value = true
  try {
    const res = await request.post('/upload', formData)
    const payload = unwrap(res)
    return payload.url
  } catch (error) {
    console.error('上传失败：', error)
    return null
  } finally {
    uploading.value = false
  }
}

async function handleOutPhoto(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  outForm.out_photo = await uploadFile(file)
}

async function handleInPhoto(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  closeForm.in_photo = await uploadFile(file)
}

onMounted(async () => {
  await loadVehicles()
  await loadData()
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

.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
