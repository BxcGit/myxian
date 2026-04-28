<template>
  <div class="dashboard">
    <div class="header-section">
      <h1>咸鱼商城控制台</h1>
      <p>管理您的账号和消息</p>
    </div>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-clickable" @click="navigateTo('/sessions')">
          <div class="stat-value">{{ sessions.length }}</div>
          <div class="stat-label">会话数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ accounts.length }}</div>
          <div class="stat-label">账号数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ products.length }}</div>
          <div class="stat-label">商品数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-clickable" @click="navigateTo('/sessions')">
          <div class="stat-value">{{ recentMessages.length }}</div>
          <div class="stat-label">未读消息</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="feature-cards">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近会话</span>
              <el-button size="small" @click="navigateTo('/sessions')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="sessions.slice(0, 5)" stripe style="width: 100%">
            <el-table-column prop="user_name" label="用户" width="120" />
            <el-table-column prop="item_id" label="商品ID" show-overflow-tooltip />
            <el-table-column label="最后消息" width="160">
              <template #default="{ row }">
                {{ formatTime(row.last_message_time) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近消息</span>
              <el-button size="small" @click="navigateTo('/sessions')">查看全部</el-button>
            </div>
          </template>
          <div class="message-list">
            <div
              v-for="msg in recentMessages.slice(0, 10)"
              :key="msg.id"
              class="message-item message-item-clickable"
              @click="navigateToSession(msg.session_id)"
            >
              <div class="message-sender">{{ msg.sender_name || '未知用户' }}</div>
              <div class="message-content">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
            </div>
            <el-empty v-if="recentMessages.length === 0" description="暂无消息" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { sessionApi } from "../api.js";
import { xianyuAccountApi } from "../api.js";
import { productApi } from "../api.js";

const router = useRouter();
const sessions = ref([]);
const recentMessages = ref([]);
const accounts = ref([]);
const products = ref([]);

async function fetchSessions() {
  try {
    const res = await sessionApi.list();
    sessions.value = res.data;
  } catch (err) {
    console.error("获取会话失败:", err);
  }
}

async function fetchRecentMessages() {
  try {
    const res = await sessionApi.getRecentMessages(100);
    recentMessages.value = res.data;
  } catch (err) {
    console.error("获取消息失败:", err);
  }
}

async function fetchAccounts() {
  try {
    const res = await xianyuAccountApi.list();
    accounts.value = res.data;
  } catch (err) {
    console.error("获取账号失败:", err);
  }
}

async function fetchProducts() {
  try {
    const res = await productApi.list();
    products.value = res.data;
  } catch (err) {
    console.error("获取商品失败:", err);
  }
}

function navigateTo(path) {
  router.push(path);
}

function navigateToSession(sessionId) {
  router.push(`/sessions?sessionId=${sessionId}`);
}

function formatTime(timestamp) {
  if (!timestamp) return "-";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

onMounted(() => {
  fetchSessions();
  fetchRecentMessages();
  fetchAccounts();
  fetchProducts();

  // 定时刷新消息
  setInterval(() => {
    fetchRecentMessages();
    fetchSessions();
  }, 10000);
});
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.header-section {
  text-align: center;
  padding: 40px 0;
  margin-bottom: 20px;
}

.header-section h1 {
  font-size: 36px;
  margin-bottom: 10px;
  color: #303133;
}

.header-section p {
  font-size: 16px;
  color: #909399;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 20px 0;
}

.stat-card-clickable {
  cursor: pointer;
  transition: transform 0.3s;
}

.stat-card-clickable:hover {
  transform: translateY(-5px);
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #ff4d4f;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.feature-cards {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.message-list {
  max-height: 300px;
  overflow-y: auto;
}

.message-item {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  transition: background-color 0.2s;
}

.message-item:hover {
  background-color: #f5f7fa;
}

.message-item-clickable {
  cursor: pointer;
}

.message-item:last-child {
  border-bottom: none;
}

.message-sender {
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.message-content {
  color: #606266;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-time {
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 4px;
}
</style>
