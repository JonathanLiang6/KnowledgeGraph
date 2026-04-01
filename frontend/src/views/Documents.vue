<template>
  <div class="documents">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        文档管理
      </h1>
      
      <div class="toolbar-actions">
        <div class="search-box">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索文档..."
            class="search-input"
            @keyup.enter="searchDocuments"
          >
          <button class="icon-btn" @click="searchDocuments">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </button>
        </div>
        
        <el-select v-model="fileTypeFilter" placeholder="类型" size="small" style="width: 100px">
          <el-option label="全部" value=""></el-option>
          <el-option label="PDF" value=".pdf"></el-option>
          <el-option label="Word" value=".doc"></el-option>
          <el-option label="文本" value=".txt"></el-option>
          <el-option label="MD" value=".md"></el-option>
        </el-select>
        
        <el-select v-model="statusFilter" placeholder="状态" size="small" style="width: 100px">
          <el-option label="全部" value=""></el-option>
          <el-option label="已处理" value="processed"></el-option>
          <el-option label="处理中" value="processing"></el-option>
          <el-option label="未处理" value="pending"></el-option>
        </el-select>
        
        <el-upload
          class="upload-btn"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          accept=".pdf,.doc,.docx,.txt,.md"
        >
          <button class="btn-primary btn-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
            </svg>
            上传
          </button>
        </el-upload>
      </div>
    </div>

    <!-- 文档列表 - 固定高度 -->
    <div class="documents-list">
      <el-table 
        :data="paginatedDocuments" 
        style="width: 100%"
        height="calc(100vh - 220px)"
        size="small"
      >
        <el-table-column prop="name" label="文档名称" min-width="180">
          <template #default="scope">
            <div class="document-name">
              <div class="file-icon" :class="getFileIconClass(scope.row.name)">
                <svg v-if="scope.row.name.endsWith('.pdf')" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                </svg>
              </div>
              <span class="name-text" :title="scope.row.name">{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="80">
          <template #default="scope">
            {{ formatFileSize(scope.row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploadTime" label="上传时间" width="140"></el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <button class="icon-btn action" @click="viewDocument(scope.row)" title="查看">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </button>
              <button class="icon-btn action process" @click="processDocument(scope.row)" v-if="scope.row.status === 'pending'" title="处理">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </button>
              <button class="icon-btn action delete" @click="deleteDocument(scope.row.id)" title="删除">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                </svg>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 底部分页 -->
    <div class="pagination-bar">
      <span class="total-text">共 {{ filteredDocuments.length }} 条</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        layout="sizes, prev, pager, next"
        :total="filteredDocuments.length"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        size="small"
      />
    </div>

    <!-- 文档详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="currentDocument.name || '文档详情'"
      width="600px"
      :before-close="handleDialogClose"
    >
      <div class="document-detail">
        <div class="detail-info">
          <div class="info-row">
            <span class="label">文件大小：</span>
            <span class="value">{{ formatFileSize(currentDocument.size) }}</span>
          </div>
          <div class="info-row">
            <span class="label">文件类型：</span>
            <span class="value">{{ currentDocument.type }}</span>
          </div>
          <div class="info-row">
            <span class="label">上传时间：</span>
            <span class="value">{{ currentDocument.uploadTime }}</span>
          </div>
          <div class="info-row" v-if="currentDocument.processedTime">
            <span class="label">处理时间：</span>
            <span class="value">{{ currentDocument.processedTime }}</span>
          </div>
          <div class="info-row">
            <span class="label">状态：</span>
            <el-tag :type="getStatusType(currentDocument.status)" size="small">{{ getStatusText(currentDocument.status) }}</el-tag>
          </div>
        </div>
        <div class="detail-stats" v-if="currentDocument.stats">
          <div class="stat-item">
            <div class="stat-value">{{ currentDocument.stats?.entities || 0 }}</div>
            <div class="stat-label">实体数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ currentDocument.stats?.relationships || 0 }}</div>
            <div class="stat-label">关系数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ currentDocument.stats?.chunks || 0 }}</div>
            <div class="stat-label">文本块</div>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="downloadDocument(currentDocument)">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
          </svg>
          下载
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// 文档数据
const documents = ref([
  {
    id: 1,
    name: '人工智能导论.pdf',
    size: 1024000,
    type: 'PDF',
    status: 'processed',
    uploadTime: '2026-03-30 10:30',
    processedTime: '2026-03-30 10:35',
    stats: {
      entities: 128,
      relationships: 256,
      chunks: 384,
      processingTime: 30
    }
  },
  {
    id: 2,
    name: '知识图谱技术.docx',
    size: 2048000,
    type: 'Word',
    status: 'processed',
    uploadTime: '2026-03-29 16:45',
    processedTime: '2026-03-29 16:50',
    stats: {
      entities: 256,
      relationships: 512,
      chunks: 768,
      processingTime: 45
    }
  },
  {
    id: 3,
    name: 'GraphRAG研究.md',
    size: 512000,
    type: 'Markdown',
    status: 'processing',
    uploadTime: '2026-03-29 14:20'
  },
  {
    id: 4,
    name: 'SQLite使用指南.txt',
    size: 256000,
    type: '文本',
    status: 'pending',
    uploadTime: '2026-03-28 09:15'
  }
])

// 搜索和筛选
const searchQuery = ref('')
const fileTypeFilter = ref('')
const statusFilter = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 对话框
const dialogVisible = ref(false)
const currentDocument = ref({})

// 过滤后的文档
const filteredDocuments = computed(() => {
  let result = [...documents.value]
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(doc => doc.name.toLowerCase().includes(query))
  }
  
  // 文件类型过滤
  if (fileTypeFilter.value) {
    result = result.filter(doc => doc.name.endsWith(fileTypeFilter.value))
  }
  
  // 状态过滤
  if (statusFilter.value) {
    result = result.filter(doc => doc.status === statusFilter.value)
  }
  
  return result
})

// 分页后的文档
const paginatedDocuments = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredDocuments.value.slice(start, end)
})

// 处理文件上传
const handleFileChange = (file) => {
  console.log('文件上传:', file)
  // 这里可以添加文件上传逻辑
  // 模拟上传成功
  const newDocument = {
    id: Date.now(),
    name: file.name,
    size: file.size,
    type: getFileExtension(file.name),
    status: 'pending',
    uploadTime: new Date().toLocaleString('zh-CN')
  }
  documents.value.unshift(newDocument)
}

// 搜索文档
const searchDocuments = () => {
  // 搜索逻辑已在computed中处理
  console.log('搜索文档:', searchQuery.value)
}

// 查看文档
const viewDocument = (document) => {
  currentDocument.value = { ...document }
  dialogVisible.value = true
}

// 处理文档
const processDocument = (document) => {
  console.log('处理文档:', document)
  // 模拟处理过程
  const index = documents.value.findIndex(doc => doc.id === document.id)
  if (index !== -1) {
    documents.value[index].status = 'processing'
    setTimeout(() => {
      documents.value[index].status = 'processed'
      documents.value[index].processedTime = new Date().toLocaleString('zh-CN')
      documents.value[index].stats = {
        entities: Math.floor(Math.random() * 200) + 100,
        relationships: Math.floor(Math.random() * 400) + 200,
        chunks: Math.floor(Math.random() * 600) + 300,
        processingTime: Math.floor(Math.random() * 30) + 15
      }
    }, 2000)
  }
}

// 删除文档
const deleteDocument = (id) => {
  console.log('删除文档:', id)
  // 模拟删除
  const index = documents.value.findIndex(doc => doc.id === id)
  if (index !== -1) {
    documents.value.splice(index, 1)
  }
}

// 下载文档
const downloadDocument = (document) => {
  console.log('下载文档:', document)
  // 这里可以添加下载逻辑
}

// 处理对话框关闭
const handleDialogClose = () => {
  dialogVisible.value = false
  currentDocument.value = {}
}

// 分页处理
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (current) => {
  currentPage.value = current
}

// 辅助函数
const getFileExtension = (filename) => {
  const ext = filename.split('.').pop().toLowerCase()
  switch (ext) {
    case 'pdf': return 'PDF'
    case 'doc':
    case 'docx': return 'Word'
    case 'txt': return '文本'
    case 'md': return 'Markdown'
    default: return '其他'
  }
}

const getFileIconClass = (filename) => {
  const ext = filename.split('.').pop().toLowerCase()
  return `file-${ext}`
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  else return (bytes / 1048576).toFixed(1) + ' MB'
}

const getStatusType = (status) => {
  switch (status) {
    case 'processed': return 'success'
    case 'processing': return 'warning'
    case 'pending': return 'info'
    default: return ''
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'processed': return '已处理'
    case 'processing': return '处理中'
    case 'pending': return '未处理'
    default: return status
  }
}
</script>

<style scoped>
.documents {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    margin-bottom: 12px;
    flex-shrink: 0;
    
    .page-title {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
    }
    
    .toolbar-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .search-box {
        display: flex;
        align-items: center;
        background: #f5f7fa;
        border-radius: 6px;
        padding: 2px 8px;
        
        .search-input {
          border: none;
          background: transparent;
          padding: 6px 8px;
          font-size: 13px;
          color: #303133;
          outline: none;
          width: 150px;
          
          &::placeholder {
            color: #909399;
          }
        }
      }
    }
  }

  .documents-list {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    flex: 1;
    overflow: hidden;
    
    .document-name {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .file-icon {
        width: 24px;
        height: 24px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        
        &.file-pdf { background: #e34c26; }
        &.file-doc, &.file-docx { background: #2b5797; }
        &.file-txt { background: #6c757d; }
        &.file-md { background: #007acc; }
      }
      
      .name-text {
        font-size: 13px;
        color: #303133;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 200px;
      }
    }
    
    .action-buttons {
      display: flex;
      gap: 4px;
    }
  }

  .pagination-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    margin-top: 12px;
    flex-shrink: 0;
    
    .total-text {
      font-size: 13px;
      color: #606266;
    }
  }

  .document-detail {
    .detail-info {
      margin-bottom: 20px;
      
      .info-row {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #f0f2f5;
        
        &:last-child {
          border-bottom: none;
        }
        
        .label {
          font-size: 12px;
          color: #606266;
          width: 80px;
          flex-shrink: 0;
        }
        
        .value {
          font-size: 12px;
          color: #303133;
        }
      }
    }
    
    .detail-stats {
      display: flex;
      gap: 16px;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      
      .stat-item {
        flex: 1;
        text-align: center;
        
        .stat-value {
          font-size: 20px;
          font-weight: 600;
          color: #667eea;
        }
        
        .stat-label {
          font-size: 12px;
          color: #909399;
          margin-top: 4px;
        }
      }
    }
  }
}

/* 按钮样式 */
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
  }
  
  &.btn-sm {
    padding: 6px 12px;
    font-size: 12px;
  }
}

.btn-secondary {
  background: #f5f7fa;
  color: #606266;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  
  &:hover {
    background: #ecf5ff;
    border-color: #c6e2ff;
    color: #409eff;
  }
}

.icon-btn {
  background: transparent;
  border: none;
  color: #606266;
  cursor: pointer;
  padding: 6px;
  border-radius: 4px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover {
    background: #f5f7fa;
    color: #409eff;
  }
  
  &.action {
    &.process:hover {
      color: #67c23a;
      background: #f0f9eb;
    }
    
    &.delete:hover {
      color: #f56c6c;
      background: #fef0f0;
    }
  }
}

.upload-btn {
  :deep(.el-upload) {
    display: block;
  }
}
</style>