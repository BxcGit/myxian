<template>
  <div class="account-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>咸鱼账号管理</span>
          <el-button type="primary" @click="showDialog('create')">新增账号</el-button>
        </div>
      </template>
      <el-table :data="accounts" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="xianyu_name" label="咸鱼账号名" />
        <el-table-column prop="cookie" label="Cookie" show-overflow-tooltip />
        <el-table-column prop="user_agent" label="User-Agent" show-overflow-tooltip />
        <el-table-column label="连接状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '已连接' : '未连接' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :loading="row._loading"
              :disabled="!row.cookie"
              @change="handleToggle(row)"
              style="margin-right: 8px;"
            />
            <el-button size="small" @click="showDialog('edit', row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="咸鱼账号名">
          <el-input v-model="form.xianyu_name" placeholder="请输入咸鱼账号名" />
        </el-form-item>
        <el-form-item label="Cookie">
          <el-input v-model="form.cookie" type="textarea" placeholder="请输入Cookie" rows="3" />
        </el-form-item>
        <el-form-item label="User-Agent">
          <el-input v-model="form.user_agent" type="textarea" placeholder="请输入User-Agent" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { xianyuAccountApi } from "../api.js";

const accounts = ref([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增账号");
const isEdit = ref(false);
const editId = ref(null);
const form = reactive({
  xianyu_name: "",
  cookie: "",
  user_agent: "",
});

async function fetchAccounts() {
  const res = await xianyuAccountApi.list();
  accounts.value = res.data;
}

function showDialog(type, row = null) {
  if (type === "create") {
    dialogTitle.value = "新增账号";
    isEdit.value = false;
    editId.value = null;
    form.xianyu_name = "";
    form.cookie = "";
    form.user_agent = "";
  } else {
    dialogTitle.value = "编辑账号";
    isEdit.value = true;
    editId.value = row.id;
    form.xianyu_name = row.xianyu_name;
    form.cookie = row.cookie;
    form.user_agent = row.user_agent || "";
  }
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!form.xianyu_name.trim()) {
    ElMessage.warning("请输入咸鱼账号名");
    return;
  }
  try {
    if (isEdit.value) {
      await xianyuAccountApi.update(editId.value, form);
      ElMessage.success("更新成功");
    } else {
      await xianyuAccountApi.create(form);
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    fetchAccounts();
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "操作失败");
  }
}

async function handleToggle(row) {
  if (!row.cookie) {
    ElMessage.warning("该账号没有Cookie，无法连接");
    row.is_active = false;
    return;
  }
  row._loading = true;
  try {
    if (row.is_active) {
      await xianyuAccountApi.start(row.id);
      ElMessage.success(`账号 ${row.xianyu_name} 已启动`);
    } else {
      await xianyuAccountApi.stop(row.id);
      ElMessage.success(`账号 ${row.xianyu_name} 已停止`);
    }
  } catch (err) {
    // 恢复原状态
    row.is_active = !row.is_active;
    ElMessage.error(err.response?.data?.detail || "操作失败");
  } finally {
    row._loading = false;
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm("确定要删除该账号吗？", "提示", {
      type: "warning",
    });
    await xianyuAccountApi.delete(id);
    ElMessage.success("删除成功");
    fetchAccounts();
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error(err.response?.data?.detail || "删除失败");
    }
  }
}

onMounted(() => {
  fetchAccounts();
});
</script>

<style scoped>
.account-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
