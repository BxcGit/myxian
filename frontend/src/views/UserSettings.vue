<template>
  <div class="user-settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户设置</span>
        </div>
      </template>

      <el-form :model="form" label-width="140px" v-if="form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>

        <el-divider>人工接管模式配置</el-divider>

        <el-form-item label="接管超时时间">
          <el-input-number v-model="form.manual_timeout" :min="60" :max="86400" :step="60" />
          <span class="form-tip">秒，超时后自动退出人工接管模式</span>
        </el-form-item>

        <el-form-item label="进入接管关键字">
          <el-input v-model="form.manual_keywords" placeholder="发送此关键字进入人工接管模式" />
          <span class="form-tip">自己发送包含此关键字的消息，进入人工接管模式</span>
        </el-form-item>

        <el-form-item label="退出接管关键字">
          <el-input v-model="form.manual_exit_keywords" placeholder="发送此关键字退出人工接管模式" />
          <span class="form-tip">自己发送包含此关键字的消息，退出人工接管模式</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存设置
          </el-button>
        </el-form-item>
      </el-form>

      <el-empty v-else description="请先登录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { userSettingsApi } from "../api.js";

const form = ref(null);
const saving = ref(false);
const username = ref(localStorage.getItem("username") || "");

async function fetchSettings() {
  if (!username.value) {
    return;
  }
  try {
    const res = await userSettingsApi.get(username.value);
    form.value = res.data;
  } catch (err) {
    console.error("获取用户设置失败:", err);
    ElMessage.error("获取用户设置失败");
  }
}

async function handleSave() {
  if (!form.value || !username.value) return;

  saving.value = true;
  try {
    await userSettingsApi.update(username.value, {
      manual_timeout: form.value.manual_timeout,
      manual_keywords: form.value.manual_keywords,
      manual_exit_keywords: form.value.manual_exit_keywords,
    });
    ElMessage.success("设置保存成功");
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  fetchSettings();
});
</script>

<style scoped>
.user-settings-page {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: 500;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
