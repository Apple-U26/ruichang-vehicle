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
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        range-separator="至"
        style="width: 280px"
        :shortcuts="dateShortcuts"
      />
      <el-select v-model="timeBasis" style="width: 140px" aria-label="时间筛选依据">
        <el-option label="按出车时间" value="departure" />
        <el-option label="按收车时间" value="return" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">
        查询
      </el-button>
      <el-button v-if="canExport" :icon="Download" @click="openReport">导出里程报告</el-button>
      <el-button v-if="report.id && report.status === 'ready'" type="success" :loading="downloading" @click="downloadReport">{{ downloading ? `正在下载 ${downloadProgress}%` : '下载已生成报告' }}</el-button>
      <el-tag v-else-if="report.id && ['queued', 'running'].includes(report.status)" type="info" @click="reportVisible = true">
        报告{{ report.status === 'queued' ? '排队中' : `生成中 ${report.progress}%` }}
      </el-tag>
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
            type="primary"
            link
            size="small"
            @click="openEdit(row)"
          >
            编辑
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

    <el-dialog v-model="reportVisible" title="导出里程报告" width="min(720px, 94vw)">
      <el-form label-width="100px">
        <el-form-item label="时间段" required>
          <el-date-picker v-model="reportForm.range" type="daterange" value-format="YYYY-MM-DD"
            start-placeholder="开始日期" end-placeholder="结束日期" range-separator="至" :shortcuts="dateShortcuts" style="width: 100%" />
        </el-form-item>
        <el-form-item label="统计依据">
          <el-radio-group v-model="reportForm.time_basis">
            <el-radio value="departure">出车时间</el-radio>
            <el-radio value="return">收车时间</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="车辆">
          <el-select v-model="reportForm.vehicle_id" filterable clearable placeholder="全部有权查看的车辆" style="width: 100%">
            <el-option v-for="vehicle in reportOptions.vehicles" :key="vehicle.id" :label="vehicle.plate_no" :value="vehicle.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="驾驶人">
          <el-select v-model="reportForm.driver_name" filterable clearable placeholder="全部姓名；按姓名精确汇总" style="width: 100%">
            <el-option v-for="name in reportOptions.drivers" :key="name" :label="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-form-item label="查询关键字"><el-input v-model="reportForm.keyword" clearable placeholder="车牌 / 驾驶人 / 事由，可清空" /></el-form-item>
        <el-form-item label="行程状态">
          <el-select v-model="reportForm.status" clearable placeholder="全部状态" style="width: 100%">
            <el-option label="已收车" value="CLOSED" /><el-option label="未收车" value="OUT" />
          </el-select>
        </el-form-item>
        <el-form-item label="照片">
          <el-select v-model="reportForm.photos" style="width: 100%">
            <el-option label="出、收车各一张代表照片（推荐）" value="representative" />
            <el-option label="全部照片" value="all" /><el-option label="不附照片" value="none" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-alert title="导出包含个人里程汇总、里程明细和照片凭证三个工作表。同名跨车辆合并，异常及未收车不计有效里程；结束日期包含当天全天。"
        type="info" :closable="false" show-icon />
      <p class="report-hint">单次最多366天、5000条记录、400张照片。后台生成，可继续使用其他功能，文件保留6小时。</p>
      <el-progress v-if="['queued', 'running'].includes(report.status)" :percentage="report.progress" :stroke-width="10" />
      <el-alert v-if="report.status === 'failed'" :title="report.message || '生成失败，请缩小范围后重试'" type="error" :closable="false" />
      <p v-if="report.status === 'ready'" class="report-ready">{{ report.filename }} 已生成{{ report.bytes ? `（${(report.bytes / 1024 / 1024).toFixed(1)} MB）` : '' }}，可下载查看。</p>
      <template v-if="downloading">
        <el-progress :percentage="downloadProgress" :stroke-width="10" />
        <p class="report-hint">正在下载，含照片的报告可能需要几分钟，请等待完成。下载中断可直接重试，无需重新生成。</p>
      </template>
      <template #footer>
        <el-button @click="reportVisible = false">关闭</el-button>
        <el-button v-if="report.status === 'ready'" type="success" :loading="downloading" @click="downloadReport">{{ downloading ? `正在下载 ${downloadProgress}%` : '下载报告' }}</el-button>
        <el-button type="primary" :loading="creatingReport" :disabled="downloading || ['queued', 'running'].includes(report.status)" @click="generateReport">生成报告</el-button>
      </template>
    </el-dialog>

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

    <el-dialog v-model="editVisible" title="编辑里程记录" width="680px">
      <el-form ref="editFormRef" :model="editForm" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆">
              <el-select v-model="editForm.vehicle_id" filterable style="width: 100%">
                <el-option
                  v-for="vehicle in vehicles"
                  :key="vehicle.id"
                  :label="`${vehicle.plate_no}（${vehicle.vehicle_code}）`"
                  :value="vehicle.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出车时间">
              <el-date-picker
                v-model="editForm.trip_date"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收车时间">
              <el-date-picker
                v-model="editForm.close_time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="editForm.status" style="width: 100%">
                <el-option label="出车中" value="OUT" />
                <el-option label="已收车" value="CLOSED" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出车里程">
              <el-input-number
                v-model="editForm.out_mileage"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收车里程">
              <el-input-number
                v-model="editForm.in_mileage"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="驾驶人">
              <el-input v-model="editForm.driver_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="异常">
              <el-switch v-model="editForm.abnormal" active-text="异常" inactive-text="正常" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出发地">
              <el-input v-model="editForm.departure" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目的地">
              <el-input v-model="editForm.destination" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="异常原因">
              <el-input v-model="editForm.abnormal_reason" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用车事由">
              <el-input v-model="editForm.purpose" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="出车照片">
              <PhotoUpload v-model="editForm.out_photo" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="收车照片">
              <PhotoUpload v-model="editForm.in_photo" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="editForm.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">
          保存修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Plus, Search } from '@element-plus/icons-vue'
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
const canExport = ['ADMIN', 'FINANCE', 'PROJECT_MANAGER', 'VEHICLE_MANAGER'].includes(userInfo.role)

const rows = ref([])
const selectedRows = ref([])
const vehicles = ref([])
const month = ref('')
const dateRange = ref(null)
const timeBasis = ref('departure')
const appliedFilters = ref({})
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)

const outVisible = ref(false)
const closeVisible = ref(false)
const editVisible = ref(false)
const closeRecordId = ref(null)
const outFormRef = ref()
const closeFormRef = ref()
const editFormRef = ref()

const outForm = reactive({
  vehicle_id: null,
  trip_date: '',
  out_mileage: 0,
  driver_name: localStorage.getItem('lastDriverName') || userInfo.real_name || '',
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

const editForm = reactive({
  id: null,
  vehicle_id: null,
  trip_date: '',
  close_time: null,
  out_mileage: 0,
  in_mileage: null,
  distance: 0,
  driver_name: '',
  departure: '',
  destination: '',
  purpose: '',
  out_photo: '',
  in_photo: '',
  status: 'OUT',
  abnormal: false,
  abnormal_reason: '',
  remark: '',
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

watch(
  () => outForm.driver_name,
  (value) => {
    if (value && String(value).trim()) {
      localStorage.setItem('lastDriverName', String(value).trim())
    }
  }
)

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const params = {
        month: month.value || undefined,
        keyword: keyword.value || undefined,
        date_from: dateRange.value?.[0] || undefined,
        date_to: dateRange.value?.[1] || undefined,
        time_basis: timeBasis.value,
    }
    const res = await request.get('/mileages', { params })
    const data = unwrap(res)
    rows.value = Array.isArray(data) ? data : []
    appliedFilters.value = { ...params }
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
    driver_name:
      localStorage.getItem('lastDriverName') || userInfo.real_name || '',
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

function openEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    vehicle_id: row.vehicle_id,
    trip_date: row.trip_date,
    close_time: row.close_time || null,
    out_mileage: Number(row.out_mileage || 0),
    in_mileage: row.in_mileage == null ? null : Number(row.in_mileage),
    distance: Number(row.distance || 0),
    driver_name: row.driver_name || '',
    departure: row.departure || '',
    destination: row.destination || '',
    purpose: row.purpose || '',
    out_photo: row.out_photo || '',
    in_photo: row.in_photo || '',
    status: row.status,
    abnormal: Boolean(row.abnormal),
    abnormal_reason: row.abnormal_reason || '',
    remark: row.remark || '',
  })
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.vehicle_id || !editForm.trip_date) {
    ElMessage.warning('请选择车辆和出车时间')
    return
  }
  if (!editForm.out_photo) {
    ElMessage.warning('请上传出车照片')
    return
  }
  saving.value = true
  try {
    await request.put(`/mileages/${editForm.id}`, {
      vehicle_id: editForm.vehicle_id,
      trip_date: editForm.trip_date,
      close_time: editForm.close_time || null,
      out_mileage: editForm.out_mileage,
      in_mileage: editForm.in_mileage,
      distance: editForm.distance,
      driver_name: editForm.driver_name || null,
      departure: editForm.departure || null,
      destination: editForm.destination || null,
      purpose: editForm.purpose || null,
      out_photo: editForm.out_photo,
      in_photo: editForm.in_photo || null,
      status: editForm.status,
      abnormal: editForm.abnormal,
      abnormal_reason: editForm.abnormal_reason || null,
      remark: editForm.remark || null,
    })
    ElMessage.success('里程记录修改成功')
    editVisible.value = false
    await Promise.all([loadData(), loadVehicles()])
  } catch (error) {
    console.error('修改里程记录失败：', error)
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

const reportVisible = ref(false)
const creatingReport = ref(false)
const downloading = ref(false)
const downloadProgress = ref(0)
const reportOptions = reactive({ vehicles: [], drivers: [] })
const reportForm = reactive({ range: [], time_basis: 'departure', vehicle_id: null, driver_name: '', keyword: '', status: null, photos: 'representative' })
const report = reactive({ id: '', status: '', progress: 0, filename: '', message: '' })
const reportStorageKey = `mileageReportJob:${userInfo.id || userInfo.username || 'current'}`
let reportTimer = null
let disposed = false
let pollFailures = 0

function dateText(value) {
  const pad = (part) => String(part).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

function monthDates(value) {
  const [year, selectedMonth] = value.split('-').map(Number)
  return [dateText(new Date(year, selectedMonth - 1, 1)), dateText(new Date(year, selectedMonth, 0))]
}

const dateShortcuts = [
  { text: '本月', value: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth(), 1), now] } },
  { text: '上月', value: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth() - 1, 1), new Date(now.getFullYear(), now.getMonth(), 0)] } },
]
watch(month, (value) => { if (value) dateRange.value = null })
watch(dateRange, (value) => { if (value?.length) month.value = '' })

async function openReport() {
  if (!['queued', 'running'].includes(report.status)) {
    const filter = appliedFilters.value
    const now = new Date()
    Object.assign(reportForm, {
      range: filter.date_from ? [filter.date_from, filter.date_to] : filter.month ? monthDates(filter.month) : [dateText(new Date(now.getFullYear(), now.getMonth(), 1)), dateText(now)],
      time_basis: filter.time_basis || 'departure', vehicle_id: null, driver_name: '', keyword: filter.keyword || '', status: null, photos: 'representative',
    })
  }
  reportVisible.value = true
  try { Object.assign(reportOptions, unwrap(await request.get('/mileage-reports/options'))) }
  catch { ElMessage.error('无法加载导出选项，请稍后重试') }
}

async function pollReport() {
  if (!report.id || disposed) return
  clearTimeout(reportTimer)
  try {
    Object.assign(report, unwrap(await request.get(`/mileage-reports/${report.id}`)))
    pollFailures = 0
    if (['queued', 'running'].includes(report.status)) reportTimer = setTimeout(pollReport, 1500)
    else if (report.status === 'ready') ElMessage.success('里程报告已生成，可下载查看')
    else if (report.status === 'failed') localStorage.removeItem(reportStorageKey)
  } catch (error) {
    if ([401, 403, 404, 410].includes(error.response?.status)) {
      localStorage.removeItem(reportStorageKey)
      report.id = ''
      report.status = ''
    } else if (++pollFailures <= 5) reportTimer = setTimeout(pollReport, 3000)
    else {
      report.status = 'failed'
      report.message = '网络暂时不可用，重新进入里程管理后可继续查看任务'
    }
  }
}

async function generateReport() {
  if (!reportForm.range?.[0] || !reportForm.range?.[1]) return ElMessage.warning('请选择开始日期和结束日期')
  creatingReport.value = true
  try {
    const payload = unwrap(await request.post('/mileage-reports', {
      date_from: reportForm.range[0], date_to: reportForm.range[1], time_basis: reportForm.time_basis,
      vehicle_id: reportForm.vehicle_id || null, driver_name: reportForm.driver_name || '', keyword: reportForm.keyword || '',
      status: reportForm.status || null, photos: reportForm.photos,
    }))
    Object.assign(report, { id: payload.id, status: payload.status, progress: 0, message: '', filename: '' })
    localStorage.setItem(reportStorageKey, payload.id)
    pollFailures = 0
    await pollReport()
  } catch (error) { ElMessage.error(error.response?.data?.detail || '未能开始生成，请稍后重试') }
  finally { creatingReport.value = false }
}

async function downloadReport() {
  if (downloading.value) return
  downloading.value = true
  downloadProgress.value = 0
  const filename = report.filename || '里程报告.xlsx'
  const expectedBytes = report.bytes
  try {
    const response = await request.get(`/mileage-reports/${report.id}/download`, {
      responseType: 'blob',
      timeout: 10 * 60 * 1000,
      onDownloadProgress(event) {
        const total = event.total || expectedBytes
        if (total) downloadProgress.value = Math.min(99, Math.floor(event.loaded * 100 / total))
      },
    })
    downloadProgress.value = 100
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
    ElMessage.success('已交给浏览器保存，请查看下载列表')
  } catch (error) {
    let message = ['ECONNABORTED', 'ETIMEDOUT'].includes(error.code)
      ? '下载超时，报告已保留，请在网络稳定后直接重试下载'
      : '下载中断，报告已保留，请稍后直接重试下载'
    try { if (error.response?.data instanceof Blob) message = JSON.parse(await error.response.data.text()).detail || message } catch {}
    ElMessage.error(message)
  } finally { downloading.value = false }
}

onBeforeUnmount(() => { disposed = true; clearTimeout(reportTimer) })
onMounted(async () => {
  await loadVehicles()
  await loadData()
  const previousJob = canExport && localStorage.getItem(reportStorageKey)
  if (previousJob) { report.id = previousJob; await pollReport() }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.report-hint { color: #68798c; font-size: 12px; line-height: 1.8; }
.report-ready { color: #207245; }

.data-table {
  margin-top: 16px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
