<template>
  <div class="chat-input-area">
    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="2"
      placeholder="输入消息..."
      @update:model-value="$emit('update:modelValue', $event)"
      @keydown.enter.ctrl="handleSend"
    />
    <el-button type="primary" @click="handleSend" :disabled="!modelValue?.trim()">
      发送
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["update:modelValue", "send"]);

function handleSend() {
  emit("send");
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px;
  border-top: 1px solid #e5e4e7;
  display: flex;
  gap: 12px;
  background: #fff;
}

.chat-input-area .el-textarea {
  flex: 1;
}
</style>
