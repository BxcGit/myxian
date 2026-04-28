<template>
  <div class="session-page">
    <el-row :gutter="0" class="session-container">
      <!-- 左侧会话列表 -->
      <el-col :span="6">
        <SessionList
          v-model:selectedAccountId="selectedAccountId"
          :sessions="filteredSessions"
          :accounts="accounts"
          :currentSessionId="currentSession?.id"
          :previews="sessionPreviews"
          @select="selectSession"
          @delete="handleDeleteSession"
        />
      </el-col>

      <!-- 右侧聊天区域 -->
      <el-col :span="18" class="chat-area-col">
        <ChatPanel
          v-if="currentSession"
          :session="currentSession"
          :messages="sessionMessages"
          :accountName="getAccountName(currentSession.xianyu_account_id)"
          @send="sendMessage"
        />
        <div v-else class="no-session-selected">
          <el-empty description="请选择一个会话" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { sessionApi, xianyuAccountApi, messageApi } from "../api.js";
import SessionList from "../components/SessionList.vue";
import ChatPanel from "../components/ChatPanel.vue";

const route = useRoute();
const sessions = ref([]);
const accounts = ref([]);
const currentSession = ref(null);
const sessionMessages = ref([]);
const selectedAccountId = ref(null);
const sessionPreviews = ref({});

const filteredSessions = computed(() => {
  if (!selectedAccountId.value) {
    return sessions.value;
  }
  return sessions.value.filter((s) => s.xianyu_account_id === selectedAccountId.value);
});

function getAccountName(accountId) {
  const account = accounts.value.find((a) => a.id === accountId);
  return account?.xianyu_name || "未知账号";
}

function selectSession(session) {
  currentSession.value = session;
}

async function handleDeleteSession(session) {
  try {
    await ElMessageBox.confirm(
      `确定要删除与「${session.user_name || '未知用户'}」的会话吗？相关消息也将被删除。`,
      "确认删除",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" }
    );
    await sessionApi.delete(session.id);
    ElMessage.success("删除成功");
    if (currentSession.value?.id === session.id) {
      currentSession.value = null;
      sessionMessages.value = [];
    }
    fetchSessions();
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error(err.response?.data?.detail || "删除失败");
    }
  }
}

async function loadSessionMessages(sessionId) {
  try {
    const res = await sessionApi.getMessages(sessionId, { limit: 200 });
    sessionMessages.value = res.data;
  } catch (err) {
    ElMessage.error("获取消息失败");
  }
}

async function sendMessage(content) {
  if (!currentSession.value) return;

  try {
    const res = await messageApi.create({
      session_id: currentSession.value.id,
      xianyu_account_id: currentSession.value.xianyu_account_id,
      is_outgoing: true,
      sender_name: getAccountName(currentSession.value.xianyu_account_id),
      content,
      message_type: "chat",
    });
    if (res.data.send_status === "failed") {
      ElMessage.error("消息发送失败，WebSocket未连接");
    } else {
      await loadSessionMessages(currentSession.value.id);
    }
  } catch (err) {
    ElMessage.error("发送失败");
  }
}

async function fetchSessions() {
  try {
    const res = await sessionApi.list();
    sessions.value = res.data;
    // 加载每个会话的最后一条消息作为预览
    for (const session of sessions.value) {
      try {
        const msgRes = await sessionApi.getLastMessage(session.id);
        if (msgRes.data?.content) {
          sessionPreviews.value[session.id] = msgRes.data.content.slice(0, 20);
        }
      } catch (e) {}
    }
  } catch (err) {
    console.error("获取会话失败:", err);
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

watch(currentSession, (newSession) => {
  if (newSession) {
    loadSessionMessages(newSession.id);
  }
});

watch(selectedAccountId, () => {
  currentSession.value = null;
  sessionMessages.value = [];
});

onMounted(() => {
  fetchSessions();
  fetchAccounts();

  // 监听 sessions 加载完成后，自动选中 query 中的 sessionId
  watch(
    sessions,
    (newSessions) => {
      if (newSessions.length > 0 && route.query.sessionId) {
        const targetId = Number(route.query.sessionId);
        const session = newSessions.find((s) => s.id === targetId);
        if (session) {
          selectSession(session);
          loadSessionMessages(session.id);
        }
      }
    },
    { immediate: true }
  );

  setInterval(() => {
    fetchSessions();
    if (currentSession.value) {
      loadSessionMessages(currentSession.value.id);
    }
  }, 5000);
});
</script>

<style scoped>
.session-page {
  height: calc(100vh - 100px);
  padding: 0;
}

.session-container {
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.chat-area-col {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.no-session-selected {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
