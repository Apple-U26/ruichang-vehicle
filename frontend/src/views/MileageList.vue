<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="车牌/驾驶人/事由"
        clearable
        style="width: 220px"
        @keyup.enter="loadData"
      />
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
      <el-button v-if="!isFinance" type="success" :icon="Plus" @click="openOut">
        出车登记
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
      <el-table-column label="出车时间" width="140">
        <template #default="{ row }">
          {{ formatDateTime(row.trip_date) }}
        </template>
      </el-table-column>
      <el-table-column label="收车时间" width="140">
        <template #default="{ row }">
          {{ formatDateTime(row.close_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="plate_no" label="车牌号" width="110" />
      <el-table-column prop="driver_name" label="驾驶人" width="100" />
      <el-table-column prop="out_mileage" label="出车里程" width="100" />
      <el-table-column prop="in_mileage" label="收车里程" width="100">
        <template #default="{ row }">
          {{ row.in_mileage ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="distance" label="本次里程" width="100" />
      <el-table-column label="出车图片" width="90">
        <template #default="{ row }">
          <AttachmentPreview :url="row.out_photo" />
        </template>
      </el-table-column>
      <el-table-column label="收车图片" width="90">
        <template #default="{ row }">
          <AttachmentPreview :url="row.in_photo" />
        </template>
      </el-table-column>
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
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'OUT' && !isFinance"
            type="primary"
            link
            size="small"
            @click="openClose(row)"
          >
            收车
          </el-button>
          <el-button
            v-if="isAdmin"
            type="danger"
            link
            size="small"
            @click="deleteRow(row)"
          >
            删除
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
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
        </el-form-item>
        <el-form-item label="出车里程" prop="out_mileage">
          <el-input-number
            v-model="outForm.out_mileage"
            :min="0"
            :precision="0"
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
          <PhotoUpload v-model="outForm.out_photo" />
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
            :precision="0"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="收车照片">
          <PhotoUpload v-model="closeForm.in_photo" />
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
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Search } from '@element-plus/icons-vue'
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
const isFinance = userInfo.role === 'FINANCE'

const rows = ref([])
const selectedRows = ref([])
const vehicles = ref([])
const month = ref('')
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)

const outVisible = ref(false)
const closeVisible = ref(false)
const closeRecordId = ref(null)
const outFormRef = ref()
const closeFormRef = ref()

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

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 16)
  }
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
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

watch(
  () => outForm.vehicle_id,
  (value) => {
    const vehicle = vehicles.value.find((item) => item.id === value)
    if (vehicle) {
      outForm.out_mileage = Number(vehicle.current_mileage || 0)
    }
  }
)

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const res = await request.get('/mileages', {
      params: {
        month: month.value || undefined,
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

function openOut() {
  const today = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  const dateText = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())} ${pad(today.getHours())}:${pad(today.getMinutes())}`
  Object.assign(outForm, {
    vehicle_id: null,
    trip_date: dateText,
    out_mileage: 0,
    driver_name: '',
    departure: '',
    destination: '',
    purpose: '',
    out_photo: '',
    remark: null,
  })
  outVisible.value = true
}

async function saveOut() {
  await outFormRef.value.validate()
  if (!outForm.out_photo) {
    ElMessage.warning('请上传出车照片')
    return
  }
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
  if (!closeForm.in_photo) {
    ElMessage.warning('请上传收车照片')
    return
  }
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

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.plate_no} 的里程记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/mileages/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除里程记录失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 条里程记录？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/mileages/batch-delete', {
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
