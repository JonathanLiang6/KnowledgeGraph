<template>
  <div class="documents-page">
    <div class="page-header">
      <h1 class="page-title">文档管理</h1>
      <div class="header-actions">
        <input
          ref="fileInput"
          type="file"
          accept=".txt,.md,.pdf,.docx"
          style="display:none"
          @change="onFileSelected"
        />
        <button class="btn-primary" @click="$refs.fileInput.click()">
          <el-icon :size="14"><Upload /></el-icon> 上传文档
        </button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" size="small" style="width: 140px" clearable @change="loadDocs">
        <el-option label="全部" value="" />
        <el-option label="处理中" value="pending,parsing,nlp_extracting,llm_refining,chunking,embedding,indexing" />
        <el-option label="已完成" value="done" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-input v-model="searchQuery" placeholder="搜索文档..." size="small" style="width: 220px" clearable />
    </div>

    <!-- 文档表格 -->
    <el-table :data="filteredDocs" style="width: 100%" v-loading="loading" empty-text="暂无文档，请先上传">
      <el-table-column prop="filename" label="文件名" min-width="200">
        <template #default="{ row }">
          <span class="file-name">{{ row.filename }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="file_type" label="类型" width="90" />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="实体 / 关系" width="120">
        <template #default="{ row }">
          {{ row.entity_count }} / {{ row.relationship_count }}
        </template>
      </el-table-column>
      <el-table-column label="上传时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button :icon="Delete" size="small" type="danger" circle @click="deleteDoc(row)" />
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="total > 20">
      <el-pagination v-model:current-page="page" :page-size="20" :total="total"
        layout="prev, pager, next" @current-change="loadDocs" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getDocuments, uploadDocument, deleteDocument } from '../api/document'
import { Upload, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const fileInput = ref(null)
const docs = ref([])
const loading = ref(false)
const filterStatus = ref('')
const searchQuery = ref('')
const page = ref(1)
const total = ref(0)

const filteredDocs = computed(() => {
  if (!searchQuery.value) return docs.value
  return docs.value.filter(d => d.filename.includes(searchQuery.value))
})

function formatSize(b) {
  if (!b) return '0 B'
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

function formatDate(d) {
  return d ? new Date(d).toLocaleString('zh-CN') : ''
}

function statusType(s) {
  return s === 'done' ? 'success' : s === 'failed' ? 'danger' : 'warning'
}

function statusLabel(s) {
  const map = {
    pending: '等待处理', parsing: '解析中',
    nlp_extracting: 'NLP 提取中', llm_refining: 'LLM 精炼中',
    chunking: '分块中', embedding: '向量化中', indexing: '索引中',
    done: '已完成', failed: '失败',
  }
  return map[s] || s
}

async function loadDocs() {
  loading.value = true
  try {
    const kbId = route.params.id
    const params = { page: page.value, page_size: 20, kb_id: kbId }
    if (filterStatus.value) params.status = filterStatus.value
    const res = await getDocuments(params)
    docs.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    console.error('加载文档列表失败:', e)
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// 原生文件上传 — axios + FormData（拦截器自动处理 Content-Type）
async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const kbId = route.params.id
  if (!kbId) {
    ElMessage.warning('知识库 ID 无效')
    resetFileInput()
    return
  }

  const fd = new FormData()
  fd.append('file', file)
  fd.append('kb_id', kbId)

  try {
    const res = await uploadDocument(fd)
    ElMessage.success(`「${res.filename}」已上传，正在处理中`)
    await loadDocs()
  } catch (e) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    resetFileInput()
  }
}

function resetFileInput() {
  if (fileInput.value) fileInput.value.value = ''
}

async function deleteDoc(doc) {
  try {
    await ElMessageBox.confirm(`确定要删除「${doc.filename}」吗？`, '确认删除', { type: 'warning' })
    await deleteDocument(doc.id)
    ElMessage.success('已删除')
    await loadDocs()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      console.error('删除文档失败:', e)
    }
  }
}

watch(() => route.params.id, () => {
  page.value = 1
  loadDocs()
})

onMounted(loadDocs)
</script>

<style scoped lang="scss">
.documents-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
  }
  .filter-bar {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }
  .file-name { font-weight: 500; }
  .pagination-bar {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-md);
  }
}
</style>
