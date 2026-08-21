<template>
  <div>
    <div class="toolbar">
      <el-date-picker
        v-model="month"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        @change="loadData"
      />
    </div>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <div class="title">车辆总数</div>
          <div class="number">{{ data.vehicle_count }}</div>
          <div class="sub">活跃 {{ data.active_vehicle_count }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">本月总里程</div>
          <div class="number">{{ data.total_mileage }} km</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">本月报销</div>
          <div class="number">¥ {{ data.total_reimbursement }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">待审核报销</div>
          <div class="number">{{ data.pending_reimbursement_count }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="second-row">
      <el-col :span="6">
        <el-card>
          <div class="title">油费</div>
          <div class="amount">¥ {{ data.fuel_amount }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">维保费</div>
          <div class="amount">¥ {{ data.maintenance_amount }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">路桥费</div>
          <div class="amount">¥ {{ data.toll_amount }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div class="title">停车及其他</div>
          <div class="amount">¥ {{ Number(data.parking_amount || 0) + Number(data.other_amount || 0) }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import request from '../api/request'

const now = new Date()
const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

const month = ref(defaultMonth)

const data = ref({
  vehicle_count: 0,
  active_vehicle_count: 0,
  total_mileage: 0,
  total_reimbursement: 0,
  pending_reimbursement_count: 0,
  fuel_amount: 0,
  maintenance_amount: 0,
  toll_amount: 0,
  parking_amount: 0,
  other_amount: 0,
  mileage_allowance_amount: 0
})

async function loadData() {
  if (!month.value) return

  try {
    const res = await request.get('/dashboard', {
      params: {
        month: month.value
      }
    })

    const payload = res.data?.data || res.data || {}
    data.value = {
      vehicle_count: 0,
      active_vehicle_count: 0,
      total_mileage: 0,
      total_reimbursement: 0,
      pending_reimbursement_count: 0,
      fuel_amount: 0,
      maintenance_amount: 0,
      toll_amount: 0,
      parking_amount: 0,
      other_amount: 0,
      mileage_allowance_amount: 0,
      ...payload,
    }
  } catch (error) {
    console.error('加载仪表盘数据失败：', error)
  }
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  margin-bottom: 20px;
}

.second-row {
  margin-top: 20px;
}

.title {
  color: #888;
  margin-bottom: 15px;
}

.number {
  color: #1769aa;
  font-size: 27px;
  font-weight: bold;
}

.amount {
  color: #e67e22;
  font-size: 24px;
  font-weight: bold;
}

.sub {
  color: #999;
  font-size: 13px;
  margin-top: 6px;
}
</style>


