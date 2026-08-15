<template>
  <div class="mobile-app">
    <header class="mobile-header">
      <div>
        <div class="app-title">瑞昌车辆管理</div>
        <div class="user-line">
          {{ user.real_name }} · {{ roleLabel }}
          <template v-if="user.plate_no"> · {{ user.plate_no }}</template>
        </div>
      </div>
      <el-button link type="danger" @click="logout">退出</el-button>
    </header>

    <nav class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <el-icon :size="20">
          <component :is="tab.icon" />
        </el-icon>
        <span>{{ tab.label }}</span>
      </button>
    </nav>

    <main class="mobile-content">
      <!-- 里程 -->
      <template v-if="activeTab === 'mileage'">
        <section class="form-section">
          <div class="section-title">出车登记</div>
          <el-form label-position="top" :model="outForm">
            <el-form-item label="车辆">
              <el-select
                v-model="outForm.vehicle_id"
                filterable
                style="width: 100%"
                :disabled="isDriver && Boolean(boundVehicleId)"
              >
                <el-option
                  v-for="item in activeVehicles"
                  :key="item.id"
                  :label="item.plate_no"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="出车日期">
              <el-date-picker
                v-model="outForm.trip_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="出车里程">
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
              <PhotoUpload v-model="outForm.out_photo" />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn"
              :loading="saving"
              @click="saveOut"
            >
              保存出车
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">待收车</div>
          <div v-if="outRecords.length === 0" class="empty-tip">暂无待收车记录</div>
          <div v-for="row in outRecords" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.trip_date }} · 出车 {{ row.out_mileage }} km</span>
            </div>
            <el-button type="success" size="small" @click="openClose(row)">
              收车
            </el-button>
          </div>
        </section>

        <section class="list-section">
          <div class="section-title">最近记录</div>
          <div v-if="mileageRows.length === 0" class="empty-tip">暂无里程记录</div>
          <div v-for="row in mileageRows.slice(0, 8)" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.trip_date }} · {{ row.distance }} km · {{ row.status === 'CLOSED' ? '已收车' : '出车中' }}</span>
            </div>
          </div>
        </section>
      </template>

      <!-- 维保 -->
      <template v-else-if="activeTab === 'maintenance'">
        <section class="form-section">
          <div class="section-title">维保登记</div>
          <el-form label-position="top" :model="maintenanceForm">
            <el-form-item label="车辆">
              <el-select
                v-model="maintenanceForm.vehicle_id"
                filterable
                style="width: 100%"
                :disabled="isDriver && Boolean(boundVehicleId)"
              >
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="item.plate_no"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="维保日期">
              <el-date-picker
                v-model="maintenanceForm.maintenance_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="当前里程">
              <el-input-number
                v-model="maintenanceForm.current_mileage"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="maintenanceForm.maintenance_type" style="width: 100%">
                <el-option label="保养" value="MAINTENANCE" />
                <el-option label="维修" value="REPAIR" />
                <el-option label="年检" value="INSPECTION" />
                <el-option label="保险" value="INSURANCE" />
              </el-select>
            </el-form-item>
            <el-form-item label="维保项目">
              <el-input v-model="maintenanceForm.items" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="金额(元)">
              <el-input-number
                v-model="maintenanceForm.amount"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="服务商">
              <el-input v-model="maintenanceForm.service_provider" />
            </el-form-item>
            <el-form-item label="下次保养里程">
              <el-input-number
                v-model="maintenanceForm.next_mileage"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="维保照片">
              <PhotoUpload v-model="maintenanceForm.attachment_url" />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn"
              :loading="saving"
              @click="saveMaintenance"
            >
              保存维保
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">最近记录</div>
          <div v-if="maintenanceRows.length === 0" class="empty-tip">暂无维保记录</div>
          <div v-for="row in maintenanceRows.slice(0, 8)" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.maintenance_date }} · {{ row.items }}</span>
            </div>
            <span class="item-amount">¥ {{ row.amount }}</span>
          </div>
        </section>
      </template>

      <!-- 违章 -->
      <template v-else-if="activeTab === 'violation'">
        <section class="form-section">
          <div class="section-title">违章登记</div>
          <el-form label-position="top" :model="violationForm">
            <el-form-item label="车辆">
              <el-select
                v-model="violationForm.vehicle_id"
                filterable
                style="width: 100%"
                :disabled="isDriver && Boolean(boundVehicleId)"
              >
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="item.plate_no"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="违章日期">
              <el-date-picker
                v-model="violationForm.violation_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="违章类型">
              <el-input v-model="violationForm.violation_type" placeholder="例如：违停、超速" />
            </el-form-item>
            <el-form-item label="违章地点">
              <el-input v-model="violationForm.location" />
            </el-form-item>
            <el-form-item label="扣分">
              <el-input-number
                v-model="violationForm.points"
                :min="0"
                :max="12"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="罚款金额">
              <el-input-number
                v-model="violationForm.fine_amount"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="违章照片">
              <PhotoUpload v-model="violationForm.attachment_url" />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn"
              :loading="saving"
              @click="saveViolation"
            >
              保存违章
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">最近记录</div>
          <div v-if="violationRows.length === 0" class="empty-tip">暂无违章记录</div>
          <div v-for="row in violationRows.slice(0, 8)" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.violation_date }} · {{ row.violation_type || '违章' }}</span>
            </div>
            <span class="item-amount">¥ {{ row.fine_amount }}</span>
          </div>
        </section>
      </template>

      <!-- 油费 -->
      <template v-else>
        <section class="form-section">
          <div class="section-title">油费登记</div>
          <el-form label-position="top" :model="fuelForm">
            <el-form-item label="车辆">
              <el-select
                v-model="fuelForm.vehicle_id"
                filterable
                style="width: 100%"
                :disabled="isDriver && Boolean(boundVehicleId)"
              >
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="item.plate_no"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="加油日期">
              <el-date-picker
                v-model="fuelForm.fuel_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="加油量(升)">
              <el-input-number
                v-model="fuelForm.liters"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="单价(元/升)">
              <el-input-number
                v-model="fuelForm.unit_price"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="金额(元)">
              <el-input-number
                v-model="fuelForm.total_amount"
                :min="0"
                :precision="2"
                style="width: 100%"
              />
              <div class="auto-tip">未填写按 ¥{{ autoFuelTotal.toFixed(2) }} 计算</div>
            </el-form-item>
            <el-form-item label="当前里程">
              <el-input-number
                v-model="fuelForm.mileage"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="加油站">
              <el-input v-model="fuelForm.station" />
            </el-form-item>
            <el-form-item label="发票号">
              <el-input v-model="fuelForm.invoice_no" />
            </el-form-item>
            <el-form-item label="油费照片">
              <PhotoUpload v-model="fuelForm.attachment_url" />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn"
              :loading="saving"
              @click="saveFuel"
            >
              保存油费
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">最近记录</div>
          <div v-if="fuelRows.length === 0" class="empty-tip">暂无油费记录</div>
          <div v-for="row in fuelRows.slice(0, 8)" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.fuel_date }} · {{ row.liters }} 升</span>
            </div>
            <span class="item-amount">¥ {{ row.total_amount }}</span>
          </div>
        </section>
      </template>
    </main>

    <el-dialog
      v-model="closeVisible"
      title="收车登记"
      width="92%"
      append-to-body
    >
      <el-form label-position="top">
        <el-form-item label="收车里程">
          <el-input-number
            v-model="closeForm.in_mileage"
            :min="closeForm.out_mileage"
            :precision="1"
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
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Camera,
  Coin,
  Tools,
  Van,
  Warning,
} from '@element-plus/icons-vue'
import request from '../api/request'

const PhotoUpload = defineComponent({
  name: 'PhotoUpload',
  props: {
    modelValue: { type: String, default: '' },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const uploading = ref(false)
    const cameraInput = ref()
    const albumInput = ref()

    async function handleFile(event) {
      const file = event.target.files?.[0]
      event.target.value = ''
      if (!file) return

      const formData = new FormData()
      formData.append('file', file)
      uploading.value = true
      try {
        const res = await request.post('/upload', formData)
        const payload = res.data?.data || res.data || {}
        emit('update:modelValue', payload.url || '')
        ElMessage.success('照片上传成功')
      } catch (error) {
        console.error('照片上传失败：', error)
      } finally {
        uploading.value = false
      }
    }

    return () =>
      h('div', { class: 'photo-upload' }, [
        h('input', {
          ref: cameraInput,
          type: 'file',
          accept: 'image/*',
          capture: 'environment',
          style: { display: 'none' },
          onChange: handleFile,
        }),
        h('input', {
          ref: albumInput,
          type: 'file',
          accept: 'image/*',
          style: { display: 'none' },
          onChange: handleFile,
        }),
        h(
          'button',
          {
            type: 'button',
            class: 'photo-btn',
            disabled: uploading.value,
            onClick: () => cameraInput.value?.click(),
          },
          uploading.value ? '上传中...' : '拍照'
        ),
        h(
          'button',
          {
            type: 'button',
            class: 'photo-btn album-btn',
            disabled: uploading.value,
            onClick: () => albumInput.value?.click(),
          },
          uploading.value ? '上传中...' : '相册'
        ),
        props.modelValue
          ? h(
              'a',
              {
                href: props.modelValue,
                target: '_blank',
                class: 'photo-link',
              },
              '查看已上传图片'
            )
          : null,
      ])
  },
})

const router = useRouter()
const activeTab = ref('mileage')
const saving = ref(false)
const closeVisible = ref(false)

const tabs = [
  { key: 'mileage', label: '里程', icon: Van },
  { key: 'maintenance', label: '维保', icon: Tools },
  { key: 'violation', label: '违章', icon: Warning },
  { key: 'fuel', label: '油费', icon: Coin },
]

let userInfo = {}
try {
  userInfo = JSON.parse(
    localStorage.getItem('userInfo') || localStorage.getItem('user') || '{}'
  )
} catch (error) {
  userInfo = {}
}
const user = ref(userInfo)
const roleLabel = computed(() => {
  const map = {
    ADMIN: '管理员',
    VEHICLE_MANAGER: '车辆管理员',
    PROJECT_MANAGER: '项目经理',
    FINANCE: '财务',
    DRIVER: '驾驶员',
  }
  return map[user.value.role] || user.value.role
})
const isDriver = computed(() => user.value.role === 'DRIVER')
const boundVehicleId = computed(() => user.value.vehicle_id || null)

const vehicles = ref([])
const mileageRows = ref([])
const maintenanceRows = ref([])
const violationRows = ref([])
const fuelRows = ref([])

const activeVehicles = computed(() =>
  vehicles.value.filter((item) => item.status === 'ACTIVE')
)

const outRecords = computed(() =>
  mileageRows.value.filter((row) => row.status === 'OUT')
)

const outForm = reactive({
  vehicle_id: null,
  trip_date: '',
  out_mileage: 0,
  driver_name: '',
  departure: '',
  destination: '',
  purpose: '',
  out_photo: '',
  remark: null,
})

const closeForm = reactive({
  id: null,
  out_mileage: 0,
  in_mileage: 0,
  in_photo: '',
})

const maintenanceForm = reactive({
  vehicle_id: null,
  maintenance_date: '',
  current_mileage: 0,
  maintenance_type: 'MAINTENANCE',
  items: '',
  amount: 0,
  service_provider: '',
  next_mileage: null,
  attachment_url: '',
  remark: null,
})

const violationForm = reactive({
  vehicle_id: null,
  violation_date: '',
  violation_type: '',
  location: '',
  points: null,
  fine_amount: 0,
  attachment_url: '',
  remark: null,
})

const fuelForm = reactive({
  vehicle_id: null,
  fuel_date: '',
  liters: 0,
  unit_price: 0,
  total_amount: 0,
  mileage: null,
  station: '',
  invoice_no: '',
  attachment_url: '',
  remark: null,
})

const autoFuelTotal = computed(
  () => Number(fuelForm.liters || 0) * Number(fuelForm.unit_price || 0)
)

function unwrap(res) {
  return res.data?.data || res.data || res
}

function todayText() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

async function loadAll() {
  const [vehicleRes, mileageRes, maintenanceRes, violationRes, fuelRes] =
    await Promise.allSettled([
      request.get('/vehicles'),
      request.get('/mileages'),
      request.get('/maintenances'),
      request.get('/violations'),
      request.get('/fuels'),
    ])

  if (vehicleRes.status === 'fulfilled') {
    const data = unwrap(vehicleRes.value)
    vehicles.value = Array.isArray(data) ? data : []
    if (boundVehicleId.value) {
      outForm.vehicle_id = boundVehicleId.value
      maintenanceForm.vehicle_id = boundVehicleId.value
      violationForm.vehicle_id = boundVehicleId.value
      fuelForm.vehicle_id = boundVehicleId.value
    }
  }
  if (mileageRes.status === 'fulfilled') {
    const data = unwrap(mileageRes.value)
    mileageRows.value = Array.isArray(data) ? data : []
  }
  if (maintenanceRes.status === 'fulfilled') {
    const data = unwrap(maintenanceRes.value)
    maintenanceRows.value = Array.isArray(data) ? data : []
  }
  if (violationRes.status === 'fulfilled') {
    const data = unwrap(violationRes.value)
    violationRows.value = Array.isArray(data) ? data : []
  }
  if (fuelRes.status === 'fulfilled') {
    const data = unwrap(fuelRes.value)
    fuelRows.value = Array.isArray(data) ? data : []
  }
}

async function saveOut() {
  if (!outForm.vehicle_id || !outForm.trip_date) {
    ElMessage.warning('请选择车辆和日期')
    return
  }
  saving.value = true
  try {
    await request.post('/mileages/out', {
      vehicle_id: outForm.vehicle_id,
      trip_date: outForm.trip_date,
      out_mileage: outForm.out_mileage,
      driver_name: outForm.driver_name || user.value.real_name,
      departure: outForm.departure || null,
      destination: outForm.destination || null,
      purpose: outForm.purpose || null,
      out_photo: outForm.out_photo || null,
      remark: outForm.remark,
    })
    ElMessage.success('出车登记成功')
    resetOutForm()
    await loadAll()
  } catch (error) {
    console.error('出车失败：', error)
  } finally {
    saving.value = false
  }
}

function openClose(row) {
  closeForm.id = row.id
  closeForm.out_mileage = Number(row.out_mileage || 0)
  closeForm.in_mileage = Number(row.out_mileage || 0)
  closeForm.in_photo = ''
  closeVisible.value = true
}

async function saveClose() {
  if (closeForm.in_mileage < closeForm.out_mileage) {
    ElMessage.warning('收车里程不能小于出车里程')
    return
  }
  saving.value = true
  try {
    await request.put(`/mileages/${closeForm.id}/close`, {
      in_mileage: closeForm.in_mileage,
      in_photo: closeForm.in_photo || null,
    })
    ElMessage.success('收车成功')
    closeVisible.value = false
    await loadAll()
  } catch (error) {
    console.error('收车失败：', error)
  } finally {
    saving.value = false
  }
}

async function saveMaintenance() {
  if (!maintenanceForm.vehicle_id || !maintenanceForm.maintenance_date) {
    ElMessage.warning('请选择车辆和日期')
    return
  }
  saving.value = true
  try {
    await request.post('/maintenances', {
      vehicle_id: maintenanceForm.vehicle_id,
      maintenance_date: maintenanceForm.maintenance_date,
      current_mileage: maintenanceForm.current_mileage,
      maintenance_type: maintenanceForm.maintenance_type,
      items: maintenanceForm.items || '未填写',
      amount: maintenanceForm.amount,
      service_provider: maintenanceForm.service_provider || null,
      operator_name: user.value.real_name,
      next_mileage: maintenanceForm.next_mileage,
      next_date: null,
      attachment_url: maintenanceForm.attachment_url || null,
      remark: maintenanceForm.remark,
    })
    ElMessage.success('维保记录保存成功')
    resetMaintenanceForm()
    await loadAll()
  } catch (error) {
    console.error('维保保存失败：', error)
  } finally {
    saving.value = false
  }
}

async function saveViolation() {
  if (!violationForm.vehicle_id || !violationForm.violation_date) {
    ElMessage.warning('请选择车辆和日期')
    return
  }
  saving.value = true
  try {
    await request.post('/violations', {
      vehicle_id: violationForm.vehicle_id,
      violation_date: violationForm.violation_date,
      violation_type: violationForm.violation_type || null,
      location: violationForm.location || null,
      points: violationForm.points,
      fine_amount: violationForm.fine_amount,
      attachment_url: violationForm.attachment_url || null,
      status: 'UNPROCESSED',
      handler_name: null,
      remark: violationForm.remark,
    })
    ElMessage.success('违章记录保存成功')
    resetViolationForm()
    await loadAll()
  } catch (error) {
    console.error('违章保存失败：', error)
  } finally {
    saving.value = false
  }
}

async function saveFuel() {
  if (!fuelForm.vehicle_id || !fuelForm.fuel_date) {
    ElMessage.warning('请选择车辆和日期')
    return
  }
  saving.value = true
  try {
    const total = Number(fuelForm.total_amount || 0)
    await request.post('/fuels', {
      vehicle_id: fuelForm.vehicle_id,
      fuel_date: fuelForm.fuel_date,
      liters: fuelForm.liters,
      unit_price: fuelForm.unit_price,
      total_amount: total > 0 ? total : autoFuelTotal.value,
      mileage: fuelForm.mileage,
      station: fuelForm.station || null,
      invoice_no: fuelForm.invoice_no || null,
      attachment_url: fuelForm.attachment_url || null,
      remark: fuelForm.remark,
    })
    ElMessage.success('油费记录保存成功')
    resetFuelForm()
    await loadAll()
  } catch (error) {
    console.error('油费保存失败：', error)
  } finally {
    saving.value = false
  }
}

function resetOutForm() {
  Object.assign(outForm, {
    vehicle_id: null,
    trip_date: todayText(),
    out_mileage: 0,
    driver_name: user.value.real_name || '',
    departure: '',
    destination: '',
    purpose: '',
    out_photo: '',
    remark: null,
  })
}

function resetMaintenanceForm() {
  Object.assign(maintenanceForm, {
    vehicle_id: null,
    maintenance_date: todayText(),
    current_mileage: 0,
    maintenance_type: 'MAINTENANCE',
    items: '',
    amount: 0,
    service_provider: '',
    next_mileage: null,
    attachment_url: '',
    remark: null,
  })
}

function resetViolationForm() {
  Object.assign(violationForm, {
    vehicle_id: null,
    violation_date: todayText(),
    violation_type: '',
    location: '',
    points: null,
    fine_amount: 0,
    attachment_url: '',
    remark: null,
  })
}

function resetFuelForm() {
  Object.assign(fuelForm, {
    vehicle_id: null,
    fuel_date: todayText(),
    liters: 0,
    unit_price: 0,
    total_amount: 0,
    mileage: null,
    station: '',
    invoice_no: '',
    attachment_url: '',
    remark: null,
  })
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  localStorage.removeItem('userInfo')
  router.push('/login')
}

onMounted(() => {
  resetOutForm()
  resetMaintenanceForm()
  resetViolationForm()
  resetFuelForm()
  loadAll()
})
</script>

<style scoped>
.mobile-app {
  min-height: 100%;
  background: #f3f5f8;
}

.mobile-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #1f2d3d;
  color: #fff;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
}

.user-line {
  font-size: 12px;
  color: #cbd5e1;
  margin-top: 4px;
}

.tab-bar {
  position: sticky;
  top: 64px;
  z-index: 9;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.tab-item {
  border: none;
  background: transparent;
  padding: 12px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  font-size: 13px;
}

.tab-item.active {
  color: #2f6fad;
  font-weight: 700;
  box-shadow: inset 0 -2px 0 #2f6fad;
}

.mobile-content {
  padding: 12px;
  padding-bottom: 40px;
}

.form-section,
.list-section {
  background: #fff;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 12px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  margin-top: 4px;
}

.list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
}

.list-item:last-child {
  border-bottom: none;
}

.item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.item-main span {
  color: #6b7280;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-amount {
  color: #e67e22;
  font-weight: 700;
  white-space: nowrap;
}

.empty-tip {
  color: #9ca3af;
  text-align: center;
  padding: 18px 0;
  font-size: 14px;
}

.auto-tip {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.photo-upload) {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

:deep(.photo-btn) {
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #374151;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 14px;
}

:deep(.album-btn) {
  background: #fff;
  color: #2f6fad;
  border: 1px solid #2f6fad;
}

:deep(.photo-link) {
  color: #2f6fad;
  font-size: 13px;
}
</style>
