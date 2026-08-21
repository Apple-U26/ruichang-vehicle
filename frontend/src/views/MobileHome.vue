<template>
  <div class="mobile-app">
    <header class="mobile-header">
      <div>
        <div class="app-title">车辆管理</div>
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
        <section v-if="!isFinance" class="form-section">
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
            <el-form-item label="出车时间">
              <el-date-picker
                v-model="outForm.trip_date"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="出车里程">
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
        <section v-if="!isFinance" class="form-section">
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
                :precision="0"
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
                :precision="0"
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
                :precision="0"
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
        <section v-if="!isFinance" class="form-section">
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
                :precision="0"
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
      <template v-else-if="activeTab === 'fuel'">
        <section v-if="!isFinance" class="form-section">
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
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="单价(元/升)">
              <el-input-number
                v-model="fuelForm.unit_price"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="金额(元)">
              <el-input-number
                v-model="fuelForm.total_amount"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
              <div class="auto-tip">未填写按 ¥{{ autoFuelTotal.toFixed(2) }} 计算</div>
            </el-form-item>
            <el-form-item label="当前里程">
              <el-input-number
                v-model="fuelForm.mileage"
                :min="0"
                :precision="0"
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

      <!-- 报销 -->
      <template v-else-if="activeTab === 'reimbursement'">
        <section v-if="!isFinance" class="form-section">
          <div class="section-title">报销申请</div>
          <el-form label-position="top" :model="reimbForm">
            <el-form-item label="报销月份">
              <el-date-picker
                v-model="reimbForm.reimbursement_month"
                type="month"
                value-format="YYYY-MM"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="车辆">
              <el-select
                v-model="reimbForm.vehicle_id"
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
            <el-form-item label="项目">
              <el-select
                v-model="reimbForm.project_id"
                clearable
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="item in projects"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="reimbForm.remark" type="textarea" :rows="2" />
            </el-form-item>

            <div class="section-title small">费用明细</div>
            <div
              v-for="(row, index) in reimbForm.details"
              :key="index"
              class="detail-row"
            >
              <el-form-item label="费用类型">
                <el-select v-model="row.expense_type" style="width: 100%">
                  <el-option label="油费" value="FUEL" />
                  <el-option label="维保费" value="MAINTENANCE" />
                  <el-option label="路桥费" value="TOLL" />
                  <el-option label="停车费" value="PARKING" />
                  <el-option label="其他" value="OTHER" />
                </el-select>
              </el-form-item>
              <el-form-item label="日期">
                <el-date-picker
                  v-model="row.expense_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="金额(元)">
                <el-input-number
                  v-model="row.amount"
                  :min="0.01"
                  :precision="0"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="说明">
                <el-input v-model="row.description" />
              </el-form-item>
              <el-form-item label="费用图片">
                <PhotoUpload v-model="row.attachment_url" />
              </el-form-item>
              <el-button
                type="danger"
                link
                size="small"
                @click="removeReimbDetail(index)"
              >
                删除该费用
              </el-button>
            </div>

            <div class="mobile-source-row">
              <el-select
                v-model="selectedMileageId"
                placeholder="选择里程记录"
                filterable
                style="flex: 1"
              >
                <el-option
                  v-for="item in mileageCandidates"
                  :key="item.id"
                  :label="`${item.trip_date} · ${item.distance} 公里 · ¥${(Number(item.distance) * 0.2).toFixed(2)}`"
                  :value="item.id"
                />
              </el-select>
              <el-button
                type="success"
                :disabled="!selectedMileageId"
                @click="addMobileMileage"
              >
                添加里程补助
              </el-button>
            </div>

            <el-button class="secondary-btn" @click="addReimbDetail">
              添加费用
            </el-button>
            <el-button
              class="submit-btn"
              type="primary"
              :loading="saving"
              @click="saveReimbursement"
            >
              保存报销
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">最近报销</div>
          <div v-if="reimbRows.length === 0" class="empty-tip">暂无报销记录</div>
          <div v-for="row in reimbRows.slice(0, 8)" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.plate_no }}</strong>
              <span>{{ row.reimbursement_month }} · {{ statusLabel(row.status) }}</span>
            </div>
            <span class="item-amount">¥ {{ row.total_amount }}</span>
          </div>
        </section>
      </template>

      <!-- 项目 -->
      <template v-else-if="activeTab === 'project'">
        <section class="form-section">
          <div class="section-title">新增项目</div>
          <el-form label-position="top" :model="projectForm">
            <el-form-item label="项目名称">
              <el-input v-model="projectForm.name" />
            </el-form-item>
            <el-form-item label="项目负责人">
              <el-input v-model="projectForm.manager_name" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="projectForm.remark" type="textarea" :rows="2" />
            </el-form-item>
            <el-button
              class="submit-btn"
              type="primary"
              :loading="saving"
              @click="saveProject"
            >
              保存项目
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">项目列表</div>
          <div v-if="projects.length === 0" class="empty-tip">暂无项目</div>
          <div v-for="row in projects" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.name }}</strong>
              <span>{{ row.manager_name || '未设置负责人' }}</span>
            </div>
            <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? '启用' : '停用' }}
            </el-tag>
          </div>
        </section>
      </template>

      <!-- 用户管理 -->
      <template v-else-if="activeTab === 'users'">
        <section class="form-section">
          <div class="section-title">
            {{ editingUserId ? '编辑用户' : '新增用户' }}
          </div>
          <el-form label-position="top" :model="userForm">
            <el-form-item label="用户名">
              <el-input v-model="userForm.username" :disabled="Boolean(editingUserId)" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="userForm.real_name" />
            </el-form-item>
            <el-form-item :label="editingUserId ? '重置密码' : '初始密码'">
              <el-input
                v-model="userForm.password"
                type="password"
                show-password
                :placeholder="editingUserId ? '留空则不修改' : '至少 6 位'"
              />
            </el-form-item>
            <el-form-item label="角色">
              <el-select v-model="userForm.role" style="width: 100%">
                <el-option label="系统管理员" value="ADMIN" />
                <el-option label="车辆负责人" value="VEHICLE_MANAGER" />
                <el-option label="项目负责人" value="PROJECT_MANAGER" />
                <el-option label="财务人员" value="FINANCE" />
                <el-option label="驾驶员" value="DRIVER" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="userForm.role === 'DRIVER'" label="绑定车辆">
              <el-select
                v-model="userForm.vehicle_id"
                clearable
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="item in vehicles"
                  :key="item.id"
                  :label="`${item.plate_no}（${item.vehicle_code}）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-switch v-model="userForm.enabled" active-text="启用" inactive-text="停用" />
            </el-form-item>
            <el-button
              class="submit-btn"
              type="primary"
              :loading="saving"
              @click="saveUser"
            >
              {{ editingUserId ? '保存修改' : '创建用户' }}
            </el-button>
          </el-form>
        </section>

        <section class="list-section">
          <div class="section-title">用户列表</div>
          <div v-for="row in users" :key="row.id" class="list-item">
            <div class="item-main">
              <strong>{{ row.username }}</strong>
              <span>
                {{ row.real_name }} · {{ roleLabelFor(row.role) }} ·
                {{ row.plate_no || '未绑定车辆' }}
              </span>
            </div>
            <el-button size="small" @click="editUser(row)">编辑</el-button>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Coin,
  FolderOpened,
  Money,
  Tools,
  User,
  Van,
  Warning,
} from '@element-plus/icons-vue'
import request from '../api/request'
import PhotoUpload from '../components/PhotoUpload.vue'

const router = useRouter()
const activeTab = ref('mileage')
const saving = ref(false)
const closeVisible = ref(false)

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
    VEHICLE_MANAGER: '车辆负责人',
    PROJECT_MANAGER: '项目负责人',
    FINANCE: '财务',
    DRIVER: '驾驶员',
  }
  return map[user.value.role] || user.value.role
})
const isDriver = computed(() => user.value.role === 'DRIVER')
const isFinance = computed(() => user.value.role === 'FINANCE')
const boundVehicleId = computed(() => user.value.vehicle_id || null)

const tabs = computed(() => {
  const role = user.value.role
  const canReimburse = ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'].includes(role)
  const canProject = ['ADMIN', 'PROJECT_MANAGER', 'FINANCE'].includes(role)
  const items = [
    { key: 'mileage', label: '里程', icon: Van },
    { key: 'maintenance', label: '维保', icon: Tools },
    { key: 'violation', label: '违章', icon: Warning },
    { key: 'fuel', label: '油费', icon: Coin },
  ]
  if (canReimburse) {
    items.push({ key: 'reimbursement', label: '报销', icon: Money })
  }
  if (canProject) {
    items.push({ key: 'project', label: '项目', icon: FolderOpened })
  }
  if (role === 'ADMIN') {
    items.push({ key: 'users', label: '用户', icon: User })
  }
  return items
})

const vehicles = ref([])
const mileageRows = ref([])
const maintenanceRows = ref([])
const violationRows = ref([])
const fuelRows = ref([])
const reimbRows = ref([])
const projects = ref([])
const users = ref([])
const editingUserId = ref(null)
const mileageCandidates = ref([])
const selectedMileageId = ref(null)

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

const reimbForm = reactive({
  reimbursement_month: '',
  vehicle_id: null,
  project_id: null,
  remark: '',
  details: [],
})

const projectForm = reactive({
  name: '',
  manager_name: '',
  remark: '',
})

const userForm = reactive({
  username: '',
  real_name: '',
  password: '',
  role: 'DRIVER',
  enabled: true,
  vehicle_id: null,
})

const autoFuelTotal = computed(
  () => Number(fuelForm.liters || 0) * Number(fuelForm.unit_price || 0)
)

function unwrap(res) {
  return res.data?.data || res.data || res
}

function statusLabel(status) {
  const map = {
    DRAFT: '草稿',
    SUBMITTED: '待审核',
    PROJECT_APPROVED: '待财务审核',
    APPROVED: '已通过',
    REJECTED: '已退回',
  }
  return map[status] || status
}

function roleLabelFor(role) {
  const map = {
    ADMIN: '系统管理员',
    VEHICLE_MANAGER: '车辆负责人',
    PROJECT_MANAGER: '项目负责人',
    FINANCE: '财务人员',
    DRIVER: '驾驶员',
  }
  return map[role] || role
}

function todayText() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function nowText() {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}

async function loadAll() {
  const [
    vehicleRes,
    mileageRes,
    maintenanceRes,
    violationRes,
    fuelRes,
    projectRes,
    reimbRes,
    userRes,
  ] =
    await Promise.allSettled([
      request.get('/vehicles'),
      request.get('/mileages'),
      request.get('/maintenances'),
      request.get('/violations'),
      request.get('/fuels'),
      request.get('/projects'),
      request.get('/reimbursements'),
      request.get('/users'),
    ])

  if (vehicleRes.status === 'fulfilled') {
    const data = unwrap(vehicleRes.value)
    vehicles.value = Array.isArray(data) ? data : []
    if (boundVehicleId.value) {
      outForm.vehicle_id = boundVehicleId.value
      maintenanceForm.vehicle_id = boundVehicleId.value
      violationForm.vehicle_id = boundVehicleId.value
      fuelForm.vehicle_id = boundVehicleId.value
      reimbForm.vehicle_id = boundVehicleId.value
    } else if (
      ['VEHICLE_MANAGER', 'PROJECT_MANAGER'].includes(user.value.role) &&
      vehicles.value.length &&
      !reimbForm.vehicle_id
    ) {
      reimbForm.vehicle_id = vehicles.value[0].id
      reimbForm.project_id = vehicles.value[0].project_id || null
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
  if (projectRes.status === 'fulfilled') {
    const data = unwrap(projectRes.value)
    projects.value = Array.isArray(data) ? data : []
  }
  if (reimbRes.status === 'fulfilled') {
    const data = unwrap(reimbRes.value)
    reimbRows.value = Array.isArray(data) ? data : []
  }
  if (userRes.status === 'fulfilled') {
    const data = unwrap(userRes.value)
    users.value = Array.isArray(data) ? data : []
  }
}

watch(
  () => reimbForm.vehicle_id,
  (vehicleId) => {
    if (!vehicleId) return
    const vehicle = vehicles.value.find((item) => item.id === vehicleId)
    if (vehicle && !reimbForm.project_id) {
      reimbForm.project_id = vehicle.project_id
    }
  }
)

watch(
  [() => reimbForm.vehicle_id, () => reimbForm.reimbursement_month],
  () => loadMileageCandidates()
)

async function saveOut() {
  if (!outForm.vehicle_id || !outForm.trip_date) {
    ElMessage.warning('请选择车辆和日期')
    return
  }
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
      driver_name: outForm.driver_name || user.value.real_name,
      departure: outForm.departure || null,
      destination: outForm.destination || null,
      purpose: outForm.purpose || null,
      out_photo: outForm.out_photo,
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
  if (!closeForm.in_photo) {
    ElMessage.warning('请上传收车照片')
    return
  }
  saving.value = true
  try {
    await request.put(`/mileages/${closeForm.id}/close`, {
      in_mileage: closeForm.in_mileage,
      in_photo: closeForm.in_photo,
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
  if (!maintenanceForm.attachment_url) {
    ElMessage.warning('请上传维保照片')
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
      attachment_url: maintenanceForm.attachment_url,
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
  if (!violationForm.attachment_url) {
    ElMessage.warning('请上传违章照片')
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
      attachment_url: violationForm.attachment_url,
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
  if (!fuelForm.attachment_url) {
    ElMessage.warning('请上传油费照片')
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
      attachment_url: fuelForm.attachment_url,
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

function addReimbDetail() {
  reimbForm.details.push({
    expense_type: 'FUEL',
    expense_date: '',
    amount: null,
    description: '',
    attachment_url: '',
  })
}

function removeReimbDetail(index) {
  reimbForm.details.splice(index, 1)
}

async function loadMileageCandidates() {
  if (!reimbForm.vehicle_id || !reimbForm.reimbursement_month) {
    mileageCandidates.value = []
    return
  }
  try {
    const res = await request.get('/mileages', {
      params: {
        vehicle_id: reimbForm.vehicle_id,
        month: reimbForm.reimbursement_month,
        exclude_used: true,
      },
    })
    const data = unwrap(res)
    mileageCandidates.value = Array.isArray(data) ? data : []
  } catch (error) {
    mileageCandidates.value = []
  }
}

function addMobileMileage() {
  const source = mileageCandidates.value.find(
    (item) => item.id === selectedMileageId.value
  )
  if (!source) return
  reimbForm.details.push({
    expense_type: 'MILEAGE_ALLOWANCE',
    expense_date: String(source.trip_date).slice(0, 10),
    amount: (Number(source.distance) * 0.2).toFixed(2),
    related_mileage: source.distance,
    invoice_no: '',
    description: `里程补助 ${source.trip_date}`,
    attachment_url:
      [source.out_photo, source.in_photo].filter(Boolean).join(',') || '',
    is_linked: true,
    source_type: 'MILEAGE',
    source_id: source.id,
    source_label: `里程 ${source.trip_date}`,
  })
  selectedMileageId.value = null
}

async function saveReimbursement() {
  if (!reimbForm.reimbursement_month || !reimbForm.vehicle_id) {
    ElMessage.warning('请选择报销月份和车辆')
    return
  }
  if (!reimbForm.details.length) {
    ElMessage.warning('请至少添加一条费用')
    return
  }
  for (const row of reimbForm.details) {
    if (!row.expense_date || !row.amount) {
      ElMessage.warning('每条费用必须填写日期、金额并上传图片')
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
      reimbursement_month: reimbForm.reimbursement_month,
      vehicle_id: reimbForm.vehicle_id,
      project_id: reimbForm.project_id,
      remark: reimbForm.remark || null,
      details: reimbForm.details.map((row) => ({
        expense_type: row.expense_type,
        expense_date: row.expense_date,
        amount: row.amount,
        related_mileage: row.related_mileage || null,
        invoice_no: null,
        description: row.description || null,
        attachment_url: row.attachment_url,
        source_type: row.source_type || null,
        source_id: row.source_id || null,
      })),
    })
    ElMessage.success('报销申请保存成功')
    resetReimbForm()
    await loadAll()
  } catch (error) {
    console.error('报销申请失败：', error)
  } finally {
    saving.value = false
  }
}

async function saveProject() {
  if (!projectForm.name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  saving.value = true
  try {
    await request.post('/projects', {
      name: projectForm.name,
      manager_name: projectForm.manager_name || null,
      remark: projectForm.remark || null,
    })
    ElMessage.success('项目保存成功')
    resetProjectForm()
    await loadAll()
  } catch (error) {
    console.error('项目保存失败：', error)
  } finally {
    saving.value = false
  }
}

function resetUserForm() {
  editingUserId.value = null
  Object.assign(userForm, {
    username: '',
    real_name: '',
    password: '',
    role: 'DRIVER',
    enabled: true,
    vehicle_id: null,
  })
}

function editUser(row) {
  editingUserId.value = row.id
  Object.assign(userForm, {
    username: row.username,
    real_name: row.real_name,
    password: '',
    role: row.role,
    enabled: Boolean(row.enabled),
    vehicle_id: row.vehicle_id,
  })
}

async function saveUser() {
  if (!userForm.username || !userForm.real_name) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  if (!editingUserId.value && (!userForm.password || userForm.password.length < 6)) {
    ElMessage.warning('初始密码至少 6 位')
    return
  }
  if (editingUserId.value && userForm.password && userForm.password.length < 6) {
    ElMessage.warning('重置密码至少 6 位')
    return
  }

  saving.value = true
  try {
    if (editingUserId.value) {
      await request.put(`/users/${editingUserId.value}`, {
        real_name: userForm.real_name,
        role: userForm.role,
        enabled: userForm.enabled,
        password: userForm.password || null,
        vehicle_id: userForm.role === 'DRIVER' ? userForm.vehicle_id : null,
      })
      ElMessage.success('用户修改成功')
    } else {
      await request.post('/users', {
        username: userForm.username,
        real_name: userForm.real_name,
        password: userForm.password,
        role: userForm.role,
        enabled: userForm.enabled,
        vehicle_id: userForm.role === 'DRIVER' ? userForm.vehicle_id : null,
      })
      ElMessage.success('用户创建成功')
    }
    resetUserForm()
    await loadAll()
  } catch (error) {
    console.error('保存用户失败：', error)
  } finally {
    saving.value = false
  }
}

function resetOutForm() {
  Object.assign(outForm, {
    vehicle_id: null,
    trip_date: nowText(),
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

function resetReimbForm() {
  selectedMileageId.value = null
  Object.assign(reimbForm, {
    reimbursement_month: '',
    vehicle_id: boundVehicleId.value || null,
    project_id: null,
    remark: '',
    details: [],
  })
}

function resetProjectForm() {
  Object.assign(projectForm, {
    name: '',
    manager_name: '',
    remark: '',
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
  resetReimbForm()
  resetProjectForm()
  resetUserForm()
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

.section-title.small {
  font-size: 14px;
  margin: 12px 0 8px;
}

.detail-row {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  margin-top: 4px;
}

.secondary-btn {
  width: 100%;
  margin-top: 8px;
}

.mobile-source-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
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

</style>
