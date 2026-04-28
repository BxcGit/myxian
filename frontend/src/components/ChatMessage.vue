<template>
  <div class="chat-message" :class="{ outgoing: message.is_outgoing, incoming: !message.is_outgoing }">
    <div class="chat-avatar">
      <el-avatar :size="36">{{ avatarText }}</el-avatar>
    </div>
    <div class="chat-bubble">
      <div class="chat-sender" v-if="!message.is_outgoing">{{ message.sender_name || '对方' }}</div>
      <div class="chat-content">
        {{ message.content }}
        <span v-if="message.send_status === 'failed'" class="send-failed">发送失败</span>
      </div>
      <div class="chat-time">{{ formatTime(message.created_at) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { formatTime } from "../utils/format";

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
});

const avatarText = computed(() => {
  if (props.message.is_outgoing) return "我";
  return props.message.sender_name?.charAt(0) || "?";
});
</script>

<style scoped>
.chat-message {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}

.chat-message.outgoing {
  flex-direction: row-reverse;
}

.chat-message.incoming {
  flex-direction: row;
}

.chat-avatar {
  margin: 0 12px;
}

.chat-bubble {
  max-width: 60%;
  padding: 12px 16px;
  border-radius: 12px;
  word-break: break-word;
}

.outgoing .chat-bubble {
  background-color: #ff4d4f;
  color: white;
  border-bottom-right-radius: 4px;
}

.incoming .chat-bubble {
  background-color: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.chat-sender {
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 4px;
}

.chat-content {
  font-size: 14px;
  line-height: 1.5;
}

.chat-time {
  font-size: 11px;
  opacity: 0.6;
  margin-top: 6px;
}

.outgoing .chat-time {
  text-align: right;
}

.incoming .chat-time {
  text-align: left;
}

.send-failed {
  font-size: 11px;
  color: #ff4d4f;
  margin-left: 6px;
  opacity: 0.8;
}
</style>
