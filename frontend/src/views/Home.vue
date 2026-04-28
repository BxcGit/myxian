<template>
  <div class="home-container">
    <el-header class="header" height="60px">
      <div class="logo">
        <el-icon><ShoppingBag /></el-icon>
        <span>咸鱼商城</span>
      </div>
      <div class="user-info">
        <span class="username">{{ currentUsername }}</span>
        <el-dropdown>
          <span class="el-dropdown-link">
            用户中心<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigateTo('/settings')">设置</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <div class="body-container">
      <el-aside class="sidebar" width="200px">
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
        >
          <el-menu-item
            v-for="item in menuItems"
            :key="item.path"
            :index="item.path"
            @click="navigateTo(item.path)"
          >
            <el-icon><component :is="iconMap[item.icon]" /></el-icon>
            <span>{{ item.name }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ShoppingBag, User, Goods, ChatDotRound } from "@element-plus/icons-vue";
import { tokenManager } from "../api.js";

const router = useRouter();
const route = useRoute();

const iconMap = { User, Goods, ShoppingBag, ChatDotRound };

// 定义菜单项（硬编码，方便扩展）
const menuItems = [
  { path: "/", name: "首页", icon: "ShoppingBag" },
  { path: "/accounts", name: "账号管理", icon: "User" },
  { path: "/sessions", name: "会话管理", icon: "ChatDotRound" },
  { path: "/products", name: "商品管理", icon: "Goods" },
];

// 高亮当前菜单
const activeMenu = computed(() => route.path);

// 显示当前用户名
const currentUsername = computed(() => tokenManager.getUsername() || "用户");

function navigateTo(path) {
  router.push(path);
}

function handleLogout() {
  tokenManager.clear();
  router.push("/login");
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 0 50px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  font-size: 24px;
  font-weight: bold;
  color: #ff4d4f;
  gap: 8px;
}

.body-container {
  display: flex;
  margin-top: 60px;
  min-height: calc(100vh - 60px);
}

.sidebar {
  background-color: #fff;
  border-right: 1px solid #e5e4e7;
  position: fixed;
  top: 60px;
  left: 0;
  bottom: 0;
  overflow-y: auto;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.main-content {
  flex: 1;
  margin-left: 200px;
  padding: 20px 50px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.el-dropdown-link {
  cursor: pointer;
  color: #333;
  display: flex;
  align-items: center;
  gap: 4px;
}

.username {
  margin-right: 10px;
  color: #666;
}
</style>
