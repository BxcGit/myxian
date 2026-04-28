<template>
  <div class="product-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>商品管理</span>
          <div class="header-actions">
            <el-select v-model="selectedAccountId" placeholder="选择账号筛选" clearable @change="handleAccountFilter" style="width: 200px; margin-right: 12px;">
              <el-option v-for="acc in accounts" :key="acc.id" :label="acc.xianyu_name" :value="acc.id" />
            </el-select>
            <el-button type="primary" @click="handleSync" :loading="syncing">同步商品</el-button>
          </div>
        </div>
      </template>

      <el-table :data="products" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="item_id" label="商品ID" width="140" show-overflow-tooltip />
        <el-table-column prop="title" label="商品标题" min-width="180" show-overflow-tooltip />
        <el-table-column label="商品描述" width="100">
          <template #default="{ row }">
            <el-popover placement="right" :width="400" trigger="hover" v-if="row.description">
              <template #reference>
                <el-button size="small">查看</el-button>
              </template>
              <div class="description-popover">{{ row.description }}</div>
            </el-popover>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="商品图片" width="100">
          <template #default="{ row }">
            <el-popover placement="right" :width="340" trigger="click" v-if="getImages(row).length > 0">
              <template #reference>
                <el-button size="small">查看</el-button>
              </template>
              <div class="image-popover">
                <el-scrollbar>
                  <div class="image-list">
                    <el-image
                      v-for="(img, idx) in getImages(row)"
                      :key="idx"
                      :src="img"
                      :preview-src-list="getImages(row)"
                      :initial-index="idx"
                      fit="cover"
                      class="product-image"
                      preview-teleported
                    />
                  </div>
                </el-scrollbar>
              </div>
            </el-popover>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="100">
          <template #default="{ row }">
            <el-popover placement="right" :width="300" trigger="click" v-if="getSkus(row).length > 0">
              <template #reference>
                <el-button size="small">查看</el-button>
              </template>
              <div class="sku-popover">
                <div v-for="(sku, idx) in getSkus(row)" :key="idx" class="sku-row">
                  <span class="sku-label">{{ sku.propertyText || '默认' }}</span>
                  <span class="sku-price">¥{{ (sku.price / 100).toFixed(2) }}</span>
                  <span class="sku-stock">x{{ sku.quantity }}</span>
                </div>
              </div>
            </el-popover>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">
            <span v-if="row.price">¥{{ (row.price / 100).toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="main_prompt" label="主提示词" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showPromptDialog(row)">编辑提示词</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="products.length === 0" description="暂无商品，请先同步" />
    </el-card>

    <!-- 编辑主提示词对话框 -->
    <el-dialog v-model="promptDialogVisible" title="编辑主提示词" width="600px">
      <el-form label-width="100px">
        <el-form-item label="商品ID">
          <span>{{ currentProduct?.item_id }}</span>
        </el-form-item>
        <el-form-item label="商品标题">
          <span>{{ currentProduct?.title }}</span>
        </el-form-item>
        <el-form-item label="商品价格">
          <span v-if="currentProduct?.price">¥{{ (currentProduct.price / 100).toFixed(2) }}</span>
          <span v-else>-</span>
        </el-form-item>
        <el-form-item label="商品描述">
          <div class="description-text">{{ currentProduct?.description }}</div>
        </el-form-item>
        <el-form-item label="SKU">
          <div class="sku-list">
            <div v-for="(sku, idx) in getSkus(currentProduct)" :key="idx" class="sku-row">
              <span class="sku-label">{{ sku.propertyText || '默认' }}</span>
              <span class="sku-price">¥{{ (sku.price / 100).toFixed(2) }}</span>
              <span class="sku-stock">库存: {{ sku.quantity }}</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="主提示词">
          <el-input
            v-model="promptForm.main_prompt"
            type="textarea"
            :rows="6"
            placeholder="输入商品的主提示词..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="promptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePrompt" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { productApi, xianyuAccountApi } from "../api.js";

const products = ref([]);
const accounts = ref([]);
const selectedAccountId = ref(null);
const promptDialogVisible = ref(false);
const currentProduct = ref(null);
const promptForm = reactive({ main_prompt: "" });
const syncing = ref(false);
const saving = ref(false);

function getImages(row) {
  try {
    return row.images ? JSON.parse(row.images) : [];
  } catch {
    return [];
  }
}

function getSkus(row) {
  try {
    return row.skus ? JSON.parse(row.skus) : [];
  } catch {
    return [];
  }
}

async function fetchProducts() {
  try {
    const res = await productApi.list(selectedAccountId.value);
    products.value = res.data;
  } catch (err) {
    console.error("获取商品失败:", err);
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

function handleAccountFilter() {
  fetchProducts();
}

function showPromptDialog(row) {
  currentProduct.value = row;
  promptForm.main_prompt = row.main_prompt || "";
  promptDialogVisible.value = true;
}

async function handleSavePrompt() {
  if (!currentProduct.value) return;

  saving.value = true;
  try {
    await productApi.updatePrompt(currentProduct.value.id, {
      main_prompt: promptForm.main_prompt,
    });
    ElMessage.success("保存成功");
    promptDialogVisible.value = false;
    fetchProducts();
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleSync() {
  if (!selectedAccountId.value) {
    ElMessage.warning("请先选择账号");
    return;
  }

  syncing.value = true;
  try {
    await productApi.sync({ xianyu_account_id: selectedAccountId.value });
    ElMessage.success("同步请求已发送");
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "同步失败");
  } finally {
    syncing.value = false;
  }
}

onMounted(() => {
  fetchProducts();
  fetchAccounts();
});
</script>

<style scoped>
.product-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.image-popover {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  max-width: 400px;
}

.product-image {
  width: 120px;
  height: 120px;
  border-radius: 6px;
  cursor: pointer;
  object-fit: cover;
  border: 1px solid #ebeef5;
  transition: transform 0.2s, box-shadow 0.2s;
}

.product-image:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.description-popover {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.sku-popover {
  background: #fff;
  border-radius: 8px;
  padding: 8px 0;
  min-width: 280px;
}

.sku-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 16px;
  transition: background-color 0.2s;
}

.sku-row:hover {
  background: #f5f7fa;
}

.sku-label {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.sku-price {
  color: #ff4d4f;
  font-weight: bold;
  font-size: 16px;
}

.sku-stock {
  color: #909399;
  font-size: 14px;
  min-width: 50px;
  text-align: right;
}

.sku-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.description-text {
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 150px;
  overflow-y: auto;
}
</style>
