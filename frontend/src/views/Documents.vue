<template>
  <div class="documents">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
        文档管理
      </h1>
      <div class="header-actions">
        <el-upload
          class="upload-btn"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          accept=".pdf,.doc,.docx,.txt,.md"
        >
          <button class="btn-primary">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            上传文档
          </button>
        </el-upload>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-filter">
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="搜索文档..."
          class="search-input"
          @keyup.enter="searchDocuments"
        >
        <button class="search-btn" @click="searchDocuments">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>
      </div>
      <div class="filter-box">
        <el-select v-model="fileTypeFilter" placeholder="文件类型">
          <el-option label="全部" value=""></el-option>
          <el-option label="PDF" value=".pdf"></el-option>
          <el-option label="Word" value=".doc"></el-option>
          <el-option label="Word" value=".docx"></el-option>
          <el-option label="文本" value=".txt"></el-option>
          <el-option label="Markdown" value=".md"></el-option>
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态">
          <el-option label="全部" value=""></el-option>
          <el-option label="已处理" value="processed"></el-option>
          <el-option label="处理中" value="processing"></el-option>
          <el-option label="未处理" value="pending"></el-option>
        </el-select>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="documents-list">
      <el-table :data="filteredDocuments" style="width: 100%">
        <el-table-column prop="name" label="文档名称" min-width="200">
          <template #default="scope">
            <div class="document-name">
              <div class="file-icon" :class="getFileIconClass(scope.row.name)">
                <svg v-if="scope.row.name.endsWith('.pdf')" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <svg v-else-if="scope.row.name.endsWith('.doc') || scope.row.name.endsWith('.docx')" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <svg v-else-if="scope.row.name.endsWith('.txt')" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <svg v-else-if="scope.row.name.endsWith('.md')" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <div class="name-text">{{ scope.row.name }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="scope">
            {{ formatFileSize(scope.row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100"></el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploadTime" label="上传时间" width="180"></el-table-column>
        <el-table-column prop="processedTime" label="处理时间" width="180" v-if="scope.row.processedTime">{{ scope.row.processedTime }}</el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <button class="action-btn view" @click="viewDocument(scope.row)">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                查看
              </button>
              <button class="action-btn process" @click="processDocument(scope.row)" v-if="scope.row.status === 'pending'">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
                处理
              </button>
              <button class="action-btn delete" @click="deleteDocument(scope.row.id)">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
                删除
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="filteredDocuments.length"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 文档详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="currentDocument.name || '文档详情'"
      width="80%"
      :before-close="handleDialogClose"
    >
      <div class="document-detail">
        <div class="detail-header">
          <div class="detail-info">
            <div class="info-item">
              <span class="label">文件大小：</span>
              <span class="value">{{ formatFileSize(currentDocument.size) }}</span>
            </div>
            <div class="info-item">
              <span class="label">文件类型：</span>
              <span class="value">{{ currentDocument.type }}</span>
            </div>
            <div class="info-item">
              <span class="label">上传时间：</span>
              <span class="value">{{ currentDocument.uploadTime }}</span>
            </div>
            <div class="info-item" v-if="currentDocument.processedTime">
              <span class="label">处理时间：</span>
              <span class="value">{{ currentDocument.processedTime }}</span>
            </div>
            <div class="info-item">
              <span class="label">状态：</span>
              <el-tag :type="getStatusType(currentDocument.status)">{{ getStatusText(currentDocument.status) }}</el-tag>
            </div>
          </div>
          <div class="detail-actions">
            <button class="btn-secondary" @click="downloadDocument(currentDocument)">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              下载
            </button>
          </div>
        </div>
        <div class="detail-content">
          <div class="content-preview">
            <h3>文档预览</h3>
            <div class="preview-placeholder">
              <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              <p>文档预览功能开发中...</p>
            </div>
          </div>
          <div class="content-stats">
            <h3>处理统计</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">{{ currentDocument.stats?.entities || 0 }}</div>
                <div class="stat-label">提取实体数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ currentDocument.stats?.relationships || 0 }}</div>
                <div class="stat-label">提取关系数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ currentDocument.stats?.chunks || 0 }}</div>
                <div class="stat-label">文本块数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ currentDocument.stats?.processingTime || 0 }}s</div>
                <div class="stat-label">处理时间</div>
              </div>
            </div>
          </div>
        </div>
      </div>
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
    name: 'Neo4j使用指南.txt',
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
const pageSize = ref(10)

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
  if (bytes < 1024) return bytes + ' B'
  else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB'
  else return (bytes / 1048576).toFixed(2) + ' MB'
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
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .header-actions {
      display: flex;
      gap: 12px;
    }
  }

  .search-filter {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    
    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }
    
    .search-box {
      display: flex;
      align-items: center;
      background: #f5f7fa;
      border-radius: 8px;
      padding: 4px 12px;
      flex: 1;
      max-width: 400px;
      
      &:hover {
        background: #ecf5ff;
      }
      
      .search-input {
        border: none;
        background: transparent;
        padding: 8px;
        font-size: 14px;
        color: #303133;
        outline: none;
        flex: 1;
        
        &::placeholder {
          color: #909399;
        }
      }
      
      .search-btn {
        background: none;
        border: none;
        color: #606266;
        cursor: pointer;
        padding: 4px;
        transition: all 0.3s ease;
        
        &:hover {
          color: #409eff;
        }
      }
    }
    
    .filter-box {
      display: flex;
      gap: 12px;
      
      @media (max-width: 768px) {
        justify-content: space-between;
      }
      
      .el-select {
        min-width: 120px;
      }
    }
  }

  .documents-list {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    margin-bottom: 24px;
    overflow: hidden;
    
    .el-table {
      border: none;
      
      th {
        background: #fafafa;
        border-bottom: 1px solid #f0f2f5;
      }
      
      tr:hover {
        background: #f5f7fa;
      }
    }
    
    .document-name {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .file-icon {
        width: 32px;
        height: 32px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        
        &.file-pdf {
          background: #e34c26;
        }
        &.file-doc,
        &.file-docx {
          background: #2b5797;
        }
        &.file-txt {
          background: #6c757d;
        }
        &.file-md {
          background: #007acc;
        }
      }
      
      .name-text {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
      }
    }
    
    .action-buttons {
      display: flex;
      gap: 8px;
      
      .action-btn {
        background: none;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        transition: all 0.3s ease;
        
        &.view {
          color: #409eff;
          border-color: #c6e2ff;
          
          &:hover {
            background: #ecf5ff;
          }
        }
        
        &.process {
          color: #67c23a;
          border-color: #c2e7b0;
          
          &:hover {
            background: #f0f9eb;
          }
        }
        
        &.delete {
          color: #f56c6c;
          border-color: #fbc4c4;
          
          &:hover {
            background: #fef0f0;
          }
        }
      }
    }
  }

  .pagination {
    display: flex;
    justify-content: flex-end;
    padding: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  .document-detail {
    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid #f0f2f5;
      
      @media (max-width: 768px) {
        flex-direction: column;
        gap: 12px;
      }
      
      .detail-info {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        
        .info-item {
          display: flex;
          align-items: center;
          gap: 8px;
          
          .label {
            font-size: 14px;
            color: #606266;
            font-weight: 500;
          }
          
          .value {
            font-size: 14px;
            color: #303133;
          }
        }
      }
      
      .detail-actions {
        display: flex;
        gap: 12px;
      }
    }
    
    .detail-content {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
      
      @media (max-width: 768px) {
        grid-template-columns: 1fr;
      }
      
      .content-preview,
      .content-stats {
        background: #fafafa;
        border-radius: 8px;
        padding: 20px;
        
        h3 {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin-bottom: 16px;
        }
      }
      
      .preview-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px 0;
        color: #909399;
        
        svg {
          margin-bottom: 16px;
          opacity: 0.5;
        }
      }
      
      .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        
        .stat-item {
          background: white;
          padding: 16px;
          border-radius: 8px;
          text-align: center;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
          
          .stat-value {
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 4px;
          }
          
          .stat-label {
            font-size: 12px;
            color: #909399;
          }
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
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
}

.btn-secondary {
  background: #f5f7fa;
  color: #606266;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    background: #ecf5ff;
    border-color: #c6e2ff;
    color: #409eff;
  }
}

.upload-btn {
  .el-upload {
    .el-upload__input {
      display: none;
    }
  }
}
</style>