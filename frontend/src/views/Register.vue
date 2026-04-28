<template>
  <div class="register-page">
    <el-card class="register-card" shadow="always">
      <div class="register-header">
        <h2>创建账号</h2>
        <p>加入咸鱼商城，开启您的交易之旅</p>
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
        <el-form-item label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            show-password
            autocomplete="off"
          />
        </el-form-item>
        <div class="form-footer">
          <el-button
            type="primary"
            native-type="submit"
            class="register-btn"
            block
            >立即注册</el-button
          >
          <div class="login-link">
            已有账号？
            <el-link type="primary" @click="goLogin">返回登录</el-link>
          </div>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import api from "../api.js";
import { User, Lock } from "@element-plus/icons-vue";

const router = useRouter();
const form = reactive({ username: "", password: "", confirmPassword: "" });

function onSubmit() {
  if (form.password !== form.confirmPassword) {
    console.error("密码不匹配");
    // 这里可以添加 Element Plus 的 ElMessage 提示
    return;
  }
  api
    .post("/auth/register", {
      username: form.username,
      password: form.password,
    }, {
      headers: {
        "Content-Type": "application/json",
      },
    })
    .then((response) => {
      console.log("注册成功", response.data);
      router.push("/login");
    })
    .catch((err) => {
      if (err.response) {
        console.error("注册失败", err.response.data);
      } else {
        console.error("请求出错", err);
      }
    });
}

function goLogin() {
  router.push("/login");
}
</script>

<style scoped>
.register-page {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.register-card {
  width: 100%;
  max-width: 400px;
  padding: 20px;
  border-radius: 12px;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h2 {
  margin-bottom: 10px;
  color: #333;
}

.register-header p {
  color: #999;
  font-size: 14px;
}

.register-btn {
  width: 100%;
  height: 40px;
  margin-top: 10px;
  font-size: 16px;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}

.form-footer {
  margin-top: 10px;
}
</style>
