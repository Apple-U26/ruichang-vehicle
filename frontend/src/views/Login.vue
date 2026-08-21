<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>车辆管理</h2>
      <p class="sub-title">一期基础版</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            size="large"
            placeholder="请输入用户名"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api/request'

const router = useRouter()
const route = useRoute()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'Admin@123456'
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}



async function handleLogin() {
  await formRef.value.validate()
  loading.value = true

  try {
    const result = await request.post('/auth/login', form)

    const data = result.data?.data || result.data || result

    if (data?.access_token) {
      localStorage.setItem('token', data.access_token)
      const userInfo = data.user || {}
      localStorage.setItem('user', JSON.stringify(userInfo))
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      router.push(
        route.query.redirect ||
          (window.innerWidth < 768 ? '/mobile' : '/dashboard')
      )
    } else if (data?.token) {
      localStorage.setItem('token', data.token)
      const userInfo = data.user || {}
      localStorage.setItem('user', JSON.stringify(userInfo))
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      router.push(
        route.query.redirect ||
          (window.innerWidth < 768 ? '/mobile' : '/dashboard')
      )
    } else {
      console.error('登录返回中没有 token：', data)
    }
  } catch (error) {
    console.error('登录失败：', error)
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(135deg, #1769aa, #36a2eb);
}

.login-card {
  width: 420px;
  padding: 25px;
}

h2 {
  text-align: center;
  margin-bottom: 8px;
}

.sub-title {
  text-align: center;
  color: #888;
  margin-bottom: 30px;
}
</style>
