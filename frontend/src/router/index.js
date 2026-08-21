import { createRouter, createWebHistory } from 'vue-router'

import Login from '../views/Login.vue'
import Layout from '../views/Layout.vue'
import Dashboard from '../views/Dashboard.vue'
import VehicleList from '../views/VehicleList.vue'
import MileageList from '../views/MileageList.vue'
import MaintenanceList from '../views/MaintenanceList.vue'
import ViolationList from '../views/ViolationList.vue'
import FuelList from '../views/FuelList.vue'
import ReimbursementList from '../views/ReimbursementList.vue'
import ProjectList from '../views/ProjectList.vue'
import UserList from '../views/UserList.vue'
import MobileHome from '../views/MobileHome.vue'
import WelderList from '../views/WelderList.vue'
import WelderInspectionList from '../views/WelderInspectionList.vue'

const routes = [
  {
    path: '/mobile',
    component: MobileHome,
  },
  {
    path: '/login',
    component: Login,
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        component: Dashboard,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
        },
      },
      {
        path: 'vehicles',
        component: VehicleList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
        },
      },
      {
        path: 'mileages',
        component: MileageList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
        },
      },
      {
        path: 'maintenances',
        component: MaintenanceList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
        },
      },
      {
        path: 'violations',
        component: ViolationList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
        },
      },
      {
        path: 'fuels',
        component: FuelList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE', 'DRIVER'],
        },
      },
      {
        path: 'reimbursements',
        component: ReimbursementList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
        },
      },
      {
        path: 'projects',
        component: ProjectList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
        },
      },
      {
        path: 'welders',
        component: WelderList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
        },
      },
      {
        path: 'welder-inspections',
        component: WelderInspectionList,
        meta: {
          roles: ['ADMIN', 'VEHICLE_MANAGER', 'PROJECT_MANAGER', 'FINANCE'],
        },
      },
      {
        path: 'users',
        component: UserList,
        meta: {
          roles: ['ADMIN'],
        },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')

  if (to.path !== '/login' && !token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.path === '/login' && token) {
    return to.query.redirect || '/dashboard'
  }

  if (to.meta?.roles) {
    let userInfo = {}
    try {
      userInfo = JSON.parse(
        localStorage.getItem('userInfo') ||
          localStorage.getItem('user') ||
          '{}'
      )
    } catch (error) {
      userInfo = {}
    }

    if (!to.meta.roles.includes(userInfo.role)) {
      return '/dashboard'
    }
  }

  return true
})

export default router
