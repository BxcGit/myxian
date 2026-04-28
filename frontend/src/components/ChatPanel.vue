<template>
  <div class="chat-panel">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <div class="chat-title">
        <span class="chat-user-name">{{ session?.user_name || '未知用户' }}</span>
        <span class="chat-item-id" v-if="session?.item_id">商品: {{ session.item_id }}</span>
      </div>
      <div class="chat-account">{{ accountName }}</div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <ChatMessage v-for="msg in messages" :key="msg.id" :message="msg" />
      <el-empty v-if="messages.length === 0" description="暂无消息" />
    </div>

    <!-- 输入区域 -->
    <ChatInput v-model="inputText" @send="handleSend" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";
import ChatMessage from "./ChatMessage.vue";
import ChatInput from "./ChatInput.vue";

const props = defineProps({
  session: {
    type: Object,
    default: null,
  },
  messages: {
    type: Array,
    default: () => [],
  },
  accountName: {
    type: String,
    default: "未知账号",
  },
});

const emit = defineEmits(["send"]);

const inputText = ref("");
const messagesRef = ref(null);

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
  }
}

function handleSend() {
  if (!inputText.value?.trim()) return;
  emit("send", inputText.value.trim());
  inputText.value = "";
}

watch(
  () => props.messages,
  () => nextTick(scrollToBottom),
  { deep: true }
);
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e4e7;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fafafa;
}

.chat-title {
  display: flex;
  flex-direction: column;
}

.chat-user-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.chat-item-id {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.chat-account {
  font-size: 14px;
  color: #ff4d4f;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}
</style>
