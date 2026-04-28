<template>
  <div class="session-item" :class="{ active: isActive }">
    <div class="session-content" @click="$emit('select')">
      <div class="session-avatar">
        <el-avatar :size="40">{{ avatarText }}</el-avatar>
      </div>
      <div class="session-info">
        <div class="session-name">{{ session.user_name || '未知用户' }}</div>
        <div class="session-preview">{{ preview }}</div>
      </div>
      <div class="session-time">{{ formatTime(session.last_message_time) }}</div>
    </div>
    <div class="session-actions">
      <el-button type="danger" size="small" :icon="Delete" circle @click.stop="$emit('delete')" />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Delete } from "@element-plus/icons-vue";
import { formatTime } from "../utils/format";

const props = defineProps({
  session: {
    type: Object,
    required: true,
  },
  preview: {
    type: String,
    default: "",
  },
  isActive: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["select", "delete"]);

const avatarText = computed(() => props.session.user_name?.charAt(0) || "?");
</script>

<style scoped>
.session-item {
  display: flex;
  align-items: center;
  padding: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.session-item:hover {
  background-color: #f5f7fa;
}

.session-item.active {
  background-color: #e6f7ff;
}

.session-content {
  flex: 1;
  display: flex;
  align-items: center;
  overflow: hidden;
}

.session-avatar {
  margin-right: 12px;
}

.session-info {
  flex: 1;
  overflow: hidden;
}

.session-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.session-preview {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-left: 12px;
}

.session-actions {
  margin-left: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}
</style>
