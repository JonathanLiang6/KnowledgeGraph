<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <div class="documents-page">
    <div class="page-header">
      <div class="header-actions">
        <!-- v2.5: 进度条 -->
        <div v-if="uploading" class="upload-progress">
          <el-progress :percentage="uploadProgress" :status="uploadStatus" :stroke-width="6"
            style="width: 200px" />
          <span class="progress-text">{{ uploadLabel }}</span>
        </div>
        <input
          ref="fileInput"
          type="file"
          multiple
          :accept="allowedAccept"
          style="display:none"
          @change="onFilesSelected"
        />
        <el-button type="primary" :loading="uploading" :disabled="uploading" @click="$refs.fileInput.click()">
          <el-icon :size="14"><Upload /></el-icon> {{ uploading ? '上传中...' : '上传文档' }}
        </el-button>
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
      <el-input v-model="searchQuery" placeholder="搜索文档..." size="small" style="width: 220px" clearable
        @input="onSearchInput" />
    </div>

    <!-- 文档表格 -->
    <!-- v4.1 (#87): 首次加载显示骨架屏（此前为空白表格+转圈） -->
    <div v-if="initialLoading" class="docs-skeleton">
      <AppSkeleton :title="true" :lines="6" />
    </div>
    <el-table v-else :data="filteredDocs" style="width: 100%" v-loading="loading" empty-text="暂无文档，请先上传">
      <el-table-column prop="filename" label="文件名" min-width="200">
        <template #default="{ row }">
          <span class="file-name">{{ row.filename }}</span>
          <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
            <el-icon class="error-icon" color="var(--color-danger)"><WarningFilled /></el-icon>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="file_type" label="类型" width="90">
        <template #default="{ row }">
          <span class="file-type-badge">{{ row.file_type }}</span>
        </template>
      </el-table-column>
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
          {{ row.entity_count || 0 }} / {{ row.relationship_count || 0 }}
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

    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next" @current-change="loadDocs" />
    </div>

    <!-- v2.5: 批量上传结果弹窗 -->
    <el-dialog v-model="batchResultVisible" title="批量上传结果" width="480px">
      <div class="batch-summary">
        <el-tag type="success" size="small">成功 {{ batchResult.succeeded }}</el-tag>
        <el-tag v-if="batchResult.duplicates" type="warning" size="small">重复 {{ batchResult.duplicates }}</el-tag>
        <el-tag v-if="batchResult.failed" type="danger" size="small">失败 {{ batchResult.failed }}</el-tag>
      </div>
      <el-table :data="batchResult.items" style="margin-top: 12px" max-height="300">
        <el-table-column prop="filename" label="文件名" min-width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.duplicate" type="warning" size="small">重复</el-tag>
            <el-tag v-else-if="row.success" type="success" size="small">成功</el-tag>
            <el-tag v-else type="danger" size="small">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="140" />
      </el-table>
      <template #footer>
        <el-button type="primary" @click="batchResultVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import AppSkeleton from '../components/AppSkeleton.vue'
import { getDocuments, uploadDocument, uploadDocumentsBatch, deleteDocument } from '../api/document'
import { Upload, Delete, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const fileInput = ref(null)
const docs = ref([])
const loading = ref(false)
const initialLoading = ref(true)  // v4.1 (#87): 首次数据就绪前的骨架屏
watch(loading, (v) => { if (!v) initialLoading.value = false })
const filterStatus = ref('')
const searchQuery = ref('')
const searchDebounce = ref(null)
const page = ref(1)
const total = ref(0)
const pageSize = 20

// ─── 上传状态 ─────────────────────────────────────────
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadLabel = ref('')

// v2.5: 批量上传结果
const batchResultVisible = ref(false)
const batchResult = ref({ succeeded: 0, failed: 0, duplicates: 0, items: [] })

// v2.5: KB 切换竞态保护
let loadRequestId = 0

// v2.5: 匹配后端 ALLOWED_EXTENSIONS
const allowedAccept = '.txt,.md,.markdown,.pdf,.docx,.pptx,.html,.htm,.epub'

const filteredDocs = computed(() => {
  if (!searchQuery.value) return docs.value
  return docs.value.filter(d => d.filename.toLowerCase().includes(searchQuery.value.toLowerCase()))
})

function formatSize(b) {
  if (!b) return '0 B'
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

function formatDate(d) {
  return d ? new Date(d).toLocaleDateString('zh-CN') : ''
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

function onSearchInput() {
  // v2.5: 搜索防抖
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  searchDebounce.value = setTimeout(() => {
    page.value = 1
    loadDocs()
  }, 300)
}

async function loadDocs() {
  loading.value = true
  const reqId = ++loadRequestId
  try {
    const kbId = route.params.id
    const params = { page: page.value, page_size: pageSize, kb_id: kbId }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchQuery.value) params.search = searchQuery.value
    const res = await getDocuments(params)
    // v2.5: 竞态保护 — 仅当请求仍然是最新时应用结果
    if (reqId !== loadRequestId) return
    docs.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    if (reqId !== loadRequestId) return
    console.error('加载文档列表失败:', e)
    ElMessage.error('加载文档列表失败')
  } finally {
    if (reqId === loadRequestId) {
      loading.value = false
    }
  }
}

// v2.5: 批量上传处理
async function onFilesSelected(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return

  const kbId = route.params.id
  if (!kbId) {
    ElMessage.warning('知识库 ID 无效')
    resetFileInput()
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadLabel.value = `准备上传 ${files.length} 个文件...`

  if (files.length === 1) {
    // 单文件上传
    await uploadSingle(files[0], kbId)
  } else {
    // 批量上传 (v2.5)
    await uploadBatch(files, kbId)
  }

  uploading.value = false
  resetFileInput()
  await loadDocs()
}

async function uploadSingle(file, kbId) {
  uploadLabel.value = `上传中: ${file.name}`
  const fd = new FormData()
  fd.append('file', file)
  fd.append('kb_id', kbId)

  try {
    const res = await uploadDocument(fd)
    uploadProgress.value = 100
    // v2.5: 处理重复响应
    if (res.duplicate) {
      uploadStatus.value = 'warning'
      uploadLabel.value = `${res.filename} — ${res.message}`
      ElMessage.warning(res.message || '文件已存在')
    } else {
      uploadStatus.value = 'success'
      uploadLabel.value = `${res.filename} — 上传成功，正在处理`
      ElMessage.success(`「${res.filename}」已上传，正在处理中`)
    }
  } catch (e) {
    uploadStatus.value = 'exception'
    uploadLabel.value = `上传失败: ${file.name}`
    ElMessage.error(e.message || '上传失败')
  }
}

async function uploadBatch(files, kbId) {
  uploadLabel.value = `上传中: ${files.length} 个文件...`
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  fd.append('kb_id', kbId)

  try {
    const res = await uploadDocumentsBatch(fd)
    uploadProgress.value = 100
    batchResult.value = {
      succeeded: res.succeeded || 0,
      failed: res.failed || 0,
      duplicates: res.duplicates || 0,
      items: res.items || [],
    }
    batchResultVisible.value = true

    if (res.failed === 0 && res.duplicates === 0) {
      uploadStatus.value = 'success'
    } else if (res.failed > 0) {
      uploadStatus.value = 'warning'
    } else {
      uploadStatus.value = 'success'
    }
    uploadLabel.value = `${res.succeeded} 成功, ${res.duplicates} 重复, ${res.failed} 失败`
  } catch (e) {
    uploadStatus.value = 'exception'
    uploadLabel.value = `批量上传失败`
    ElMessage.error(e.message || '批量上传失败')
    // 即使批量失败，也尝试加载列表
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

// v2.5: KB 切换时带竞态保护的加载
watch(() => route.params.id, (newId, oldId) => {
  if (newId !== oldId) {
    page.value = 1
    searchQuery.value = ''
    filterStatus.value = ''
    loadDocs()
  }
})

onMounted(loadDocs)

// v2.5: 清理
onBeforeUnmount(() => {
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  loadRequestId = -1  // 使任何进行中的请求无效
})
</script>

<style scoped lang="scss">
.documents-page {
  min-height: 100vh;
  padding: var(--spacing-lg);

  .page-header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: var(--spacing-md);
    flex-wrap: wrap;
    gap: 12px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .upload-progress {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 14px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-light);
    box-shadow: var(--shadow-xs);
    animation: fadeInUp 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;

    :deep(.el-progress-bar__inner) {
      background: var(--color-primary-gradient) !important;
      background-size: 200% 100% !important;
      animation: gradient-flow 2s linear infinite !important;
    }

    .progress-text {
      font-size: 12px;
      color: var(--text-secondary);
      white-space: nowrap;
    }
  }
  .filter-bar {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-xs);
  }
  .file-name {
    font-weight: 500;
    transition: color var(--transition-fast);

    // 行 hover 时文件名变绿
    :deep(.el-table__row:hover) & {
      color: var(--color-primary);
    }
  }
  .file-type-badge {
    display: inline-block;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: var(--color-primary);
    background: var(--color-success-bg);
    border-radius: var(--radius-xs);
    text-transform: uppercase;
    font-family: var(--font-mono);
  }
  .error-icon {
    margin-left: 6px;
    cursor: help;
    animation: dot-pulse 2s ease-in-out infinite;
  }
  .pagination-bar {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-md);
  }
  .batch-summary {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    padding: var(--spacing-sm);
    background: var(--bg-page);
    border-radius: var(--radius-sm);
  }
}
</style>

/* v4.1 (#87): 文档列表骨架屏 */
.docs-skeleton {
  padding: 8px 0;
}
