<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-header">
        <h2>欢迎回来</h2>
        <p>请登录您的账号以继续</p>
      </div>
      <el-form :model="form" @submit.prevent="onSubmit" label-position="top">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            autocomplete="off"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            autocomplete="off"
          />
        </el-form-item>
        <div class="form-footer">
          <el-button type="primary" native-type="submit" class="login-btn" block
            >登录</el-button
          >
          <div class="register-link">
            还没有账号？
            <el-link type="primary" @click="goRegister">立即注册</el-link>
          </div>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { authApi, tokenManager } from "../api.js";

const router = useRouter();
const form = reactive({ username: "", password: "" });

async function onSubmit() {
  try {
    const response = await authApi.login({
      username: form.username,
      password: form.password,
    });
    const { access_token, user_id, username } = response.data;
    // 保存 token 和用户信息到 localStorage
    tokenManager.setToken(access_token);
    tokenManager.setUserId(user_id);
    tokenManager.setUsername(username);
    ElMessage.success("登录成功");
    router.push("/");
  } catch (err) {
    if (err.response) {
      const detail = err.response.data?.detail || "登录失败";
      ElMessage.error(detail);
    } else {
      ElMessage.error("网络错误，请稍后重试");
    }
  }
}

function goRegister() {
  router.push("/register");
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 20px;
  border-radius: 12px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  margin-bottom: 10px;
  color: #333;
}

.login-header p {
  color: #999;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  height: 40px;
  margin-top: 10px;
  font-size: 16px;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}

.form-footer {
  margin-top: 10px;
}
</style>
