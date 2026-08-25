<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="logo">
        <span class="logo-mark">瑞</span>
        车辆管理
      </div>

      <el-menu
        router
        :default-active="$route.path"
        background-color="#1f2d3d"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        class="side-menu"
      >
        <el-menu-item
          v-for="item in menus"
          :key="item.path"
          :index="item.path"
        >
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <span class="header-title">车辆管理</span>

        <div class="header-actions">
          <span class="user-name">{{ user.real_name }}</span>
          <el-tag size="small" type="info">
            {{ roleLabel }}
          </el-tag>

          <el-button link type="primary" @click="passwordVisible = true">
            <el-icon style="margin-right: 4px">
              <Key />
            </el-icon>
            修改密码
          </el-button>

          <el-button link type="primary" @click="router.push('/mobile')">
            <el-icon style="margin-right: 4px">
              <Iphone />
            </el-icon>
            手机端
          </el-button>

          <el-button link type="danger" @click="logout">
            <el-icon style="margin-right: 4px">
              <SwitchButton />
            </el-icon>
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
      <el-footer class="app-footer">
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">
          津ICP备2026011740号-1
        </a>
        <span class="footer-sep">|</span>
        <a
          href="https://beian.mps.gov.cn/#/query/webSearch?code=12011402001763"
          target="_blank"
          rel="noopener"
          class="police-link"
        >
          <img src="/police-badge.png" alt="公安备案" class="police-icon" />
          津公网安备12011402001763号
        </a>
      </el-footer>
    </el-container>

    <el-dialog
      v-model="passwordVisible"
      title="修改密码"
      width="440px"
      @closed="resetPasswordForm"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="90px"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="passwordLoading"
          @click="changePassword"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Aim,
  DataBoard,
  Coin,
  FolderOpened,
  Iphone,
  Key,
  Money,
  Odometer,
  Operation,
  SwitchButton,
  Tools,
  User,
  Van,
  Warning,
} from '@element-plus/icons-vue'
import request from '../api/request'

const router = useRouter()

const roleLabels = {
  ADMIN: '系统管理员',
  VEHICLE_MANAGER: '车辆负责人',
  PROJECT_MANAGER: '项目负责人',
  FINANCE: '财务人员',
  DRIVER: '驾驶员',
}

const user = ref({})
const rawUser = localStorage.getItem('userInfo') || localStorage.getItem('user')

if (rawUser) {
  try {
    user.value = JSON.parse(rawUser) || {}
  } catch (error) {
    user.value = {}
  }
}

const role = computed(() => user.value.role || 'DRIVER')
const roleLabel = computed(() => roleLabels[role.value] || role.value)

const menus = computed(() => {
  const items = [
    {
      path: '/dashboard',
      label: '首页仪表盘',
      icon: DataBoard,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
    },
    {
      path: '/vehicles',
      label: '车辆档案',
      icon: Van,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
    },
    {
      path: '/mileages',
      label: '里程管理',
      icon: Odometer,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
    },
    {
      path: '/maintenances',
      label: '维保管理',
      icon: Tools,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
    },
    {
      path: '/violations',
      label: '违章管理',
      icon: Warning,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
    },
    {
      path: '/fuels',
      label: '油费管理',
      icon: Coin,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
    },
    {
      path: '/reimbursements',
      label: '报销管理',
      icon: Money,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
    },
    {
      path: '/projects',
      label: '项目管理',
      icon: FolderOpened,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
    },
    {
      path: '/welders',
      label: '焊机档案',
      icon: Aim,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
    },
    {
      path: '/welder-inspections',
      label: '焊机巡检',
      icon: Operation,
      roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
    },
    {
      path: '/users',
      label: '用户管理',
      icon: User,
      roles: ['ADMIN'],
    },
  ]

  return items.filter((item) => item.roles.includes(role.value))
})

const passwordVisible = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
  ],
}

function resetPasswordForm() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
}

async function changePassword() {
  await passwordFormRef.value.validate()

  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  passwordLoading.value = true
  try {
    await request.post('/auth/change-password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功')
    passwordVisible.value = false
  } catch (error) {
    console.error('修改密码失败：', error)
  } finally {
    passwordLoading.value = false
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  localStorage.removeItem('userInfo')
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100%;
}

.el-aside {
  background: #1f2d3d;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  flex: none;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-mark {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #2f6fad;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.side-menu {
  border-right: none;
  flex: 1;
}

.side-menu :deep(.el-menu-item) {
  height: 48px;
}

.app-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: #374151;
}

.app-main {
  background: #f3f5f8;
  padding: 18px;
}

.app-footer {
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  color: #8a94a6;
  font-size: 12px;
}

.app-footer a {
  color: #5f6b7a;
  text-decoration: none;
}

.footer-sep {
  margin: 0 8px;
  color: #c0c8d4;
}

.police-link {
  display: inline-flex;
  align-items: center;
}

.police-icon {
  width: 16px;
  height: 16px;
  margin-right: 4px;
  vertical-align: middle;
}
</style>
