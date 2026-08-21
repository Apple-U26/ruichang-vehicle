<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="单号/车牌/申请人"
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
      <el-select
        v-model="statusFilter"
        placeholder="报销状态"
        clearable
        style="width: 170px"
      >
        <el-option
          v-for="item in statusOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">
        查询
      </el-button>
      <el-button type="success" :icon="Plus" @click="openCreateDialog">
        新建报销单
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
      <el-button
        v-if="canBatchApprove"
        type="success"
        :icon="Check"
        :disabled="!selectedRows.length"
        @click="batchApprove"
      >
        批量通过
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
      <el-table-column prop="reimbursement_no" label="报销单号" width="180" />
      <el-table-column prop="reimbursement_month" label="月份" width="90" />
      <el-table-column prop="plate_no" label="车牌号" width="110" />
      <el-table-column prop="applicant_name" label="申请人" width="100" />
      <el-table-column prop="total_amount" label="金额(元)" width="110" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTagType(row.status)">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reject_reason" label="退回原因" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.reject_reason || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" :icon="View" @click="openDetail(row)">
            查看
          </el-button>
          <el-button
            v-if="canSubmit(row)"
            type="success"
            link
            size="small"
            @click="submit(row)"
          >
            提交
          </el-button>
          <el-button
            v-if="canApprove(row)"
            type="success"
            link
            size="small"
            @click="approve(row)"
          >
            通过
          </el-button>
          <el-button
            v-if="canReject(row)"
            type="danger"
            link
            size="small"
            @click="openActionDialog(row, 'reject')"
          >
            退回
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

    <el-dialog v-model="createVisible" title="新建报销单" width="820px" @closed="resetCreateForm">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="报销月份" prop="reimbursement_month">
              <el-date-picker
                v-model="createForm.reimbursement_month"
                type="month"
                value-format="YYYY-MM"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="车辆" prop="vehicle_id">
              <el-select v-model="createForm.vehicle_id" filterable style="width: 100%">
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="item.plate_no"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目">
              <el-select v-model="createForm.project_id" clearable filterable style="width: 100%">
                <el-option
                  v-for="item in projects"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="createForm.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">费用明细</el-divider>

        <div class="source-buttons">
          <el-button
            :icon="Coin"
            :disabled="!createForm.vehicle_id || !createForm.reimbursement_month"
            @click="openSourceDialog('fuel')"
          >
            从油费记录添加
          </el-button>
          <el-button
            :icon="Tools"
            :disabled="!createForm.vehicle_id || !createForm.reimbursement_month"
            @click="openSourceDialog('maintenance')"
          >
            从维保记录添加
          </el-button>
          <el-button
            :icon="Odometer"
            :disabled="!createForm.vehicle_id || !createForm.reimbursement_month"
            @click="openSourceDialog('mileage')"
          >
            从里程记录添加
          </el-button>
          <span class="source-tip">手动费用必须上传图片证明</span>
        </div>

        <el-table :data="createForm.details" border size="small">
          <el-table-column label="来源" width="190">
            <template #default="{ row }">
              <el-tag v-if="row.is_linked" size="small" type="success">
                {{ row.source_label }}
              </el-tag>
              <el-tag v-else size="small" type="info">手动添加</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="费用类型" width="120">
            <template #default="{ row }">
              <el-select v-model="row.expense_type" size="small" :disabled="row.is_linked">
                <el-option
                  v-for="item in expenseTypes"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="日期" width="140">
            <template #default="{ row }">
              <el-date-picker
                v-model="row.expense_date"
                type="date"
                value-format="YYYY-MM-DD"
                size="small"
                :disabled="row.is_linked"
              />
            </template>
          </el-table-column>
          <el-table-column label="金额(元)" width="130">
            <template #default="{ row }">
              <el-input-number
                v-model="row.amount"
                :min="0.01"
                :precision="0"
                size="small"
                :disabled="row.is_linked"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="关联里程" width="130">
            <template #default="{ row }">
              <el-input-number
                v-model="row.related_mileage"
                :min="0"
                :precision="0"
                size="small"
                :disabled="row.is_linked"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="发票号" min-width="130">
            <template #default="{ row }">
              <el-input v-model="row.invoice_no" size="small" :disabled="row.is_linked" />
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.description" size="small" :disabled="row.is_linked" />
            </template>
          </el-table-column>
          <el-table-column label="附件" width="190">
            <template #default="{ row }">
              <AttachmentPreview
                v-if="row.is_linked && row.attachment_url"
                :url="row.attachment_url"
              />
              <span v-else-if="row.is_linked">关联记录</span>
              <PhotoUpload v-else v-model="row.attachment_url" />
            </template>
          </el-table-column>
          <el-table-column label="" width="60">
            <template #default="{ $index }">
              <el-button
                type="danger"
                link
                size="small"
                :icon="Delete"
                @click="removeDetail($index)"
              />
            </template>
          </el-table-column>
        </el-table>

        <el-button class="add-detail" :icon="Plus" @click="addDetail">
          添加费用
        </el-button>
      </el-form>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createReimbursement">
          保存草稿
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="sourceDialogVisible"
      :title="sourceDialogTitle"
      width="520px"
      @closed="selectedSourceId = null"
    >
      <el-select
        v-model="selectedSourceId"
        placeholder="请选择记录"
        filterable
        style="width: 100%"
      >
        <el-option
          v-for="item in sourceCandidates"
          :key="item.id"
          :label="sourceOptionLabel(item)"
          :value="item.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedSourceId" @click="addLinkedDetail">
          添加
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="actionVisible"
      :title="actionTitle"
      width="460px"
      @closed="resetActionForm"
    >
      <el-form ref="actionFormRef" :model="actionForm" :rules="actionRules" label-width="90px">
        <el-form-item :label="actionForm.isReject ? '退回原因' : '审核意见'" prop="opinion">
          <el-input
            v-model="actionForm.opinion"
            type="textarea"
            :rows="3"
            :placeholder="actionForm.isReject ? '请输入退回原因' : '请输入审核意见'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="actionVisible = false">取消</el-button>
        <el-button
          :type="actionForm.isReject ? 'danger' : 'primary'"
          :loading="saving"
          @click="submitAction"
        >
          确认
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="报销单详情" size="680px">
      <template v-if="detail">
        <el-descriptions :column="2" border class="detail-header">
          <el-descriptions-item label="报销单号">
            {{ detail.reimbursement_no }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusTagType(detail.status)">
              {{ statusLabel(detail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="月份">
            {{ detail.reimbursement_month }}
          </el-descriptions-item>
          <el-descriptions-item label="车牌号">
            {{ detail.plate_no }}
          </el-descriptions-item>
          <el-descriptions-item label="申请人">
            {{ detail.applicant_name }}
          </el-descriptions-item>
          <el-descriptions-item label="总金额">
            ¥ {{ detail.total_amount }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.project_name" label="项目">
            {{ detail.project_name }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.reject_reason" label="退回原因">
            {{ detail.reject_reason }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">费用明细</el-divider>
        <el-table :data="detail.details" border size="small">
          <el-table-column prop="expense_type" label="类型" width="100">
            <template #default="{ row }">
              {{ expenseLabel(row.expense_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="expense_date" label="日期" width="110" />
          <el-table-column prop="amount" label="金额" width="100" />
          <el-table-column prop="related_mileage" label="里程" width="90">
            <template #default="{ row }">
              {{ row.related_mileage ?? '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="invoice_no" label="发票号" width="130">
            <template #default="{ row }">
              {{ row.invoice_no || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip />
          <el-table-column label="附件" width="90">
            <template #default="{ row }">
              <AttachmentPreview :url="row.attachment_url" />
            </template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">审批记录</el-divider>
        <el-timeline v-if="detail.approvals?.length">
          <el-timeline-item
            v-for="item in detail.approvals"
            :key="item.id"
            :timestamp="formatDate(item.created_at)"
            placement="top"
          >
            <div class="approval-item">
              <strong>{{ approvalLabel(item.action) }}</strong>
              <span>{{ item.approver_name }}</span>
              <p v-if="item.opinion">{{ item.opinion }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无审批记录" :image-size="80" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check,
  Coin,
  Delete,
  Odometer,
  Plus,
  Search,
  Tools,
  View,
} from '@element-plus/icons-vue'
import request from '../api/request'
import AttachmentPreview from '../components/AttachmentPreview.vue'
import PhotoUpload from '../components/PhotoUpload.vue'

const rows = ref([])
const selectedRows = ref([])
const vehicles = ref([])
const projects = ref([])
const month = ref('')
const statusFilter = ref('')
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)

const createVisible = ref(false)
const createFormRef = ref()
const actionVisible = ref(false)
const actionFormRef = ref()
const detailVisible = ref(false)
const detail = ref(null)

let actionRecordId = null
let actionType = ''

let userInfo = {}
try {
  userInfo = JSON.parse(
    localStorage.getItem('userInfo') || localStorage.getItem('user') || '{}'
  )
} catch (error) {
  userInfo = {}
}
const userRole = computed(() => userInfo.role || 'DRIVER')
const userId = computed(() => userInfo.id)
const isAdmin = computed(() => userRole.value === 'ADMIN')
const canBatchApprove = computed(() =>
  ['ADMIN', 'PROJECT_MANAGER', 'FINANCE'].includes(userRole.value)
)

const statusOptions = [
  { value: 'DRAFT', label: '草稿' },
  { value: 'SUBMITTED', label: '待项目审核' },
  { value: 'PROJECT_APPROVED', label: '待财务审核' },
  { value: 'APPROVED', label: '已通过' },
  { value: 'REJECTED', label: '已退回' },
]

const expenseTypes = [
  { value: 'FUEL', label: '油费' },
  { value: 'MAINTENANCE', label: '维保费' },
  { value: 'TOLL', label: '路桥费' },
  { value: 'PARKING', label: '停车费' },
  { value: 'OTHER', label: '其他' },
  { value: 'MILEAGE_ALLOWANCE', label: '里程补助' },
]

const createForm = reactive({
  reimbursement_month: '',
  vehicle_id: null,
  project_id: null,
  remark: '',
  details: [],
})

const createRules = {
  reimbursement_month: [{ required: true, message: '请选择月份', trigger: 'change' }],
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
}

const fuelCandidates = ref([])
const maintenanceCandidates = ref([])
const mileageCandidates = ref([])
const sourceDialogVisible = ref(false)
const sourceDialogKind = ref('fuel')
const selectedSourceId = ref(null)

const actionForm = reactive({
  opinion: '',
  isReject: false,
})

const actionRules = {
  opinion: [{ required: true, message: '请输入内容', trigger: 'blur' }],
}

const actionTitle = computed(() => {
  if (!actionType) return ''
  const map = {
    'project-approve': '项目审核通过',
    'finance-approve': '财务审核通过',
    reject: '退回报销单',
  }
  return map[actionType] || ''
})

const sourceCandidates = computed(() => {
  const kind = sourceDialogKind.value
  const sourceType =
    kind === 'fuel' ? 'FUEL' : kind === 'maintenance' ? 'MAINTENANCE' : 'MILEAGE'
  const usedIds = new Set(
    createForm.details
      .filter((item) => item.source_type === sourceType && item.source_id)
      .map((item) => item.source_id)
  )
  const list =
    kind === 'fuel'
      ? fuelCandidates.value
      : kind === 'maintenance'
        ? maintenanceCandidates.value
        : mileageCandidates.value
  return list.filter((item) => !usedIds.has(item.id))
})
const sourceDialogTitle = computed(() => {
  const map = {
    fuel: '选择油费记录',
    maintenance: '选择维保记录',
    mileage: '选择里程记录',
  }
  return map[sourceDialogKind.value] || '选择记录'
})

function unwrap(res) {
  return res.data?.data || res.data || res
}

function statusLabel(status) {
  const map = {
    DRAFT: '草稿',
    SUBMITTED: '待项目审核',
    PROJECT_APPROVED: '待财务审核',
    APPROVED: '已通过',
    REJECTED: '已退回',
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    DRAFT: 'info',
    SUBMITTED: 'warning',
    PROJECT_APPROVED: 'warning',
    APPROVED: 'success',
    REJECTED: 'danger',
  }
  return map[status] || ''
}

function expenseLabel(type) {
  const map = {
    FUEL: '油费',
    MAINTENANCE: '维保费',
    TOLL: '路桥费',
    PARKING: '停车费',
    OTHER: '其他',
    MILEAGE_ALLOWANCE: '里程补助',
  }
  return map[type] || type
}

function approvalLabel(action) {
  const map = {
    SUBMIT: '提交',
    PROJECT_APPROVE: '项目审核通过',
    FINANCE_APPROVE: '财务审核通过',
    REJECT: '退回',
  }
  return map[action] || action
}

function formatDate(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

async function loadData() {
  loading.value = true
  try {
    selectedRows.value = []
    const res = await request.get('/reimbursements', {
      params: {
        month: month.value || undefined,
        status: statusFilter.value || undefined,
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

async function loadOptions() {
  const [vehicleRes, projectRes] = await Promise.allSettled([
    request.get('/vehicles'),
    request.get('/projects'),
  ])
  if (vehicleRes.status === 'fulfilled') {
    const data = unwrap(vehicleRes.value)
    vehicles.value = Array.isArray(data) ? data : []
  }
  if (projectRes.status === 'fulfilled') {
    const data = unwrap(projectRes.value)
    projects.value = Array.isArray(data) ? data : []
  }
}

async function loadSourceRecords() {
  if (!createForm.vehicle_id || !createForm.reimbursement_month) {
    fuelCandidates.value = []
    maintenanceCandidates.value = []
    mileageCandidates.value = []
    return
  }

  const params = {
    vehicle_id: createForm.vehicle_id,
    month: createForm.reimbursement_month,
    exclude_used: true,
  }
  const [fuelRes, maintenanceRes, mileageRes] = await Promise.allSettled([
    request.get('/fuels', { params }),
    request.get('/maintenances', { params }),
    request.get('/mileages', { params }),
  ])

  if (fuelRes.status === 'fulfilled') {
    const data = unwrap(fuelRes.value)
    fuelCandidates.value = Array.isArray(data) ? data : []
  } else {
    fuelCandidates.value = []
  }
  if (maintenanceRes.status === 'fulfilled') {
    const data = unwrap(maintenanceRes.value)
    maintenanceCandidates.value = Array.isArray(data) ? data : []
  } else {
    maintenanceCandidates.value = []
  }
  if (mileageRes.status === 'fulfilled') {
    const data = unwrap(mileageRes.value)
    mileageCandidates.value = Array.isArray(data) ? data : []
  } else {
    mileageCandidates.value = []
  }
}

watch(
  [() => createForm.vehicle_id, () => createForm.reimbursement_month],
  () => loadSourceRecords()
)

watch(
  () => createForm.vehicle_id,
  (vehicleId) => {
    if (!vehicleId) return
    const vehicle = vehicles.value.find((item) => item.id === vehicleId)
    if (vehicle && !createForm.project_id) {
      createForm.project_id = vehicle.project_id
    }
  }
)

function addDetail() {
  createForm.details.push({
    expense_type: 'FUEL',
    expense_date: '',
    amount: null,
    related_mileage: null,
    invoice_no: '',
    description: '',
    attachment_url: null,
    is_linked: false,
    source_type: null,
    source_id: null,
    source_label: '',
  })
}

function sourceOptionLabel(item) {
  if (sourceDialogKind.value === 'fuel') {
    return `${item.fuel_date} · ${item.liters} 升 · ¥${item.total_amount}`
  }
  if (sourceDialogKind.value === 'maintenance') {
    return `${item.maintenance_date} · ${item.items || '维保记录'} · ¥${item.amount}`
  }
  return `${item.trip_date} · ${item.distance} 公里 · 补助 ¥${(Number(item.distance) * 0.2).toFixed(2)}`
}

function openSourceDialog(kind) {
  sourceDialogKind.value = kind
  selectedSourceId.value = null
  sourceDialogVisible.value = true
}

function addLinkedDetail() {
  const source = sourceCandidates.value.find(
    (item) => item.id === selectedSourceId.value
  )
  if (!source) return

  const kind = sourceDialogKind.value
  const isFuel = kind === 'fuel'
  const isMileage = kind === 'mileage'
  createForm.details.push({
    expense_type: isMileage
      ? 'MILEAGE_ALLOWANCE'
      : isFuel
        ? 'FUEL'
        : 'MAINTENANCE',
    expense_date: isMileage
      ? String(source.trip_date).slice(0, 10)
      : isFuel
        ? source.fuel_date
        : source.maintenance_date,
    amount: isMileage
      ? Number(Number(source.distance) * 0.2).toFixed(2)
      : isFuel
        ? Number(source.total_amount)
        : Number(source.amount),
    related_mileage: isMileage
      ? source.distance
      : isFuel
        ? source.mileage
        : source.current_mileage,
    invoice_no: isFuel ? source.invoice_no || '' : '',
    description: isMileage
      ? `里程补助 ${source.trip_date}`
      : isFuel
        ? `油费记录 ${source.fuel_date}`
        : source.items || '维保记录',
    attachment_url: isMileage
      ? [source.out_photo, source.in_photo].filter(Boolean).join(',') || null
      : source.attachment_url || null,
    is_linked: true,
    source_type: isMileage ? 'MILEAGE' : isFuel ? 'FUEL' : 'MAINTENANCE',
    source_id: source.id,
    source_label: isMileage
      ? `里程 ${source.trip_date}`
      : isFuel
        ? `油费 ${source.fuel_date}`
        : `维保 ${source.maintenance_date}`,
  })
  sourceDialogVisible.value = false
}

function removeDetail(index) {
  createForm.details.splice(index, 1)
}

function resetCreateForm() {
  createForm.reimbursement_month = ''
  createForm.vehicle_id = null
  createForm.project_id = null
  createForm.remark = ''
  createForm.details = []
}

function openCreateDialog() {
  resetCreateForm()
  if (
    ['VEHICLE_MANAGER', 'PROJECT_MANAGER'].includes(userRole.value) &&
    vehicles.value.length
  ) {
    createForm.vehicle_id = vehicles.value[0].id
    const vehicle = vehicles.value[0]
    if (vehicle.project_id) {
      createForm.project_id = vehicle.project_id
    }
  }
  createVisible.value = true
}

async function createReimbursement() {
  await createFormRef.value.validate()

  if (!createForm.details.length) {
    ElMessage.warning('请至少填写一条费用')
    return
  }

  for (const row of createForm.details) {
    if (!row.expense_date || !row.amount) {
      ElMessage.warning('请完整填写每条费用的日期和金额')
      return
    }
    if (!row.is_linked && !row.attachment_url) {
      ElMessage.warning('手动费用必须上传图片证明')
      return
    }
  }

  saving.value = true
  try {
    await request.post('/reimbursements', {
      reimbursement_month: createForm.reimbursement_month,
      vehicle_id: createForm.vehicle_id,
      project_id: createForm.project_id,
      remark: createForm.remark || null,
      details: createForm.details.map((row) => ({
        expense_type: row.expense_type,
        expense_date: row.expense_date,
        amount: row.amount,
        related_mileage: row.related_mileage,
        invoice_no: row.invoice_no || null,
        description: row.description || null,
        attachment_url: row.attachment_url,
        source_type: row.source_type || null,
        source_id: row.source_id || null,
      })),
    })
    ElMessage.success('报销单创建成功')
    createVisible.value = false
    await loadData()
  } catch (error) {
    console.error('创建报销单失败：', error)
  } finally {
    saving.value = false
  }
}

function canSubmit(row) {
  return (
    ['DRAFT', 'REJECTED'].includes(row.status) &&
    (row.applicant_id === userId.value || userRole.value === 'ADMIN')
  )
}

function canApprove(row) {
  return (
    (row.status === 'SUBMITTED' &&
      ['ADMIN', 'PROJECT_MANAGER'].includes(userRole.value)) ||
    (row.status === 'PROJECT_APPROVED' &&
      ['ADMIN', 'FINANCE'].includes(userRole.value))
  )
}

function canReject(row) {
  return (
    (row.status === 'SUBMITTED' &&
      ['ADMIN', 'PROJECT_MANAGER'].includes(userRole.value)) ||
    (row.status === 'PROJECT_APPROVED' &&
      ['ADMIN', 'FINANCE'].includes(userRole.value))
  )
}

async function submit(row) {
  try {
    const res = await request.post(`/reimbursements/${row.id}/submit`)
    ElMessage.success(res.data?.message || '提交成功')
    await loadData()
  } catch (error) {
    console.error('提交失败：', error)
  }
}

async function approve(row) {
  saving.value = true
  try {
    const endpoint =
      row.status === 'SUBMITTED' ? 'project-approve' : 'finance-approve'
    const res = await request.post(
      `/reimbursements/${row.id}/${endpoint}`,
      { opinion: null }
    )
    ElMessage.success(res.data?.message || '审核通过')
    await loadData()
  } catch (error) {
    console.error('审核失败：', error)
  } finally {
    saving.value = false
  }
}

function openActionDialog(row, type) {
  actionRecordId = row.id
  actionType = type
  actionForm.isReject = type === 'reject'
  actionForm.opinion = ''
  actionVisible.value = true
}

function resetActionForm() {
  actionRecordId = null
  actionType = ''
  actionForm.opinion = ''
  actionForm.isReject = false
}

async function submitAction() {
  await actionFormRef.value.validate()
  saving.value = true
  try {
    if (actionType === 'reject') {
      const res = await request.post(`/reimbursements/${actionRecordId}/reject`, {
        reason: actionForm.opinion,
      })
      ElMessage.success(res.data?.message || '已退回')
    } else {
      const res = await request.post(
        `/reimbursements/${actionRecordId}/${actionType}`,
        { opinion: actionForm.opinion }
      )
      ElMessage.success(res.data?.message || '审核通过')
    }
    actionVisible.value = false
    await loadData()
  } catch (error) {
    console.error('操作失败：', error)
  } finally {
    saving.value = false
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除报销单 ${row.reimbursement_no}？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.delete(`/reimbursements/${row.id}`)
    ElMessage.success(res.data?.message || '删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除报销单失败：', error)
    }
  }
}

async function batchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 张报销单？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/reimbursements/batch-delete', {
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

async function batchApprove() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认批量通过选中的 ${selectedRows.value.length} 张报销单？`,
      '提示',
      { type: 'warning' }
    )
    const res = await request.post('/reimbursements/batch-approve', {
      ids: selectedRows.value.map((row) => row.id),
      opinion: '批量审核通过',
    })
    ElMessage.success(res.data?.message || '批量通过成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量审核失败：', error)
    }
  }
}

async function openDetail(row) {
  try {
    const res = await request.get(`/reimbursements/${row.id}`)
    detail.value = unwrap(res)
    detailVisible.value = true
  } catch (error) {
    console.error('加载详情失败：', error)
  }
}

onMounted(() => {
  loadOptions()
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

.source-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.source-tip {
  color: #e6a23c;
  font-size: 13px;
}

.add-detail {
  margin-top: 12px;
}

.detail-header {
  margin-bottom: 8px;
}

.approval-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
