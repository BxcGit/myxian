<template>
  <div class="session-list-panel">
    <div class="session-list-header">
      <el-select
        :model-value="selectedAccountId"
        placeholder="选择账号"
        clearable
        @update:model-value="$emit('update:selectedAccountId', $event)"
      >
        <el-option v-for="acc in accounts" :key="acc.id" :label="acc.xianyu_name" :value="acc.id" />
      </el-select>
    </div>
    <div class="session-list">
      <SessionItem
        v-for="session in sessions"
        :key="session.id"
        :session="session"
        :preview="previews[session.id] || ''"
        :isActive="currentSessionId === session.id"
        @select="$emit('select', session)"
        @delete="$emit('delete', session)"
      />
      <el-empty v-if="sessions.length === 0" description="暂无会话" />
    </div>
  </div>
</template>

<script setup>
import SessionItem from "./SessionItem.vue";

defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  accounts: {
    type: Array,
    default: () => [],
  },
  selectedAccountId: {
    type: Number,
    default: null,
  },
  currentSessionId: {
    type: Number,
    default: null,
  },
  previews: {
    type: Object,
    default: () => ({}),
  },
});

defineEmits(["update:selectedAccountId", "select", "delete"]);
</script>

<style scoped>
.session-list-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e4e7;
}

.session-list-header {
  padding: 12px;
  border-bottom: 1px solid #e5e4e7;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}
</style>
