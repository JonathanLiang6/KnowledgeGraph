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
    </div>

    <!-- 操作面板 -->
    <div class="operation-panel">
      <div class="search-and-filters">
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
        
        <div class="filters">
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
        </div>
      </div>
      
      <div class="upload-buttons">
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
            </svg>
            上传文件
          </button>
        </el-upload>
        
        <button class="btn-secondary" @click="selectFolder">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h16z"></path>
          </svg>
          上传文件夹
        </button>
        
        <input 
          type="file" 
          ref="folderInput" 
          style="display: none" 
          webkitdirectory 
          directory 
          @change="handleFolderChange"
        >
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
              <div class="name-container">
                <span class="name-text" :title="scope.row.name">{{ scope.row.name }}</span>
                <span v-if="scope.row.path" class="path-text" :title="scope.row.path">{{ scope.row.path }}</span>
              </div>
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
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <button class="icon-btn action" @click="viewDocument(scope.row)" title="查看">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
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
import { ref, computed, onMounted } from 'vue'

// 文档数据
const documents = ref([])
const loading = ref(false)

// 加载文档列表
const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8013/api/documents')
    if (!response.ok) {
      throw new Error('获取文档列表失败')
    }
    const data = await response.json()
    documents.value = data.documents
  } catch (error) {
    console.error('加载文档失败:', error)
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载文档
onMounted(() => {
  loadDocuments()
})

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
const handleFileChange = async (file) => {
  console.log('文件上传:', file)
  
  try {
    // 创建FormData对象
    const formData = new FormData()
    formData.append('file', file.raw)
    
    // 调用后端上传接口
    const response = await fetch('http://localhost:8013/api/documents/upload', {
      method: 'POST',
      body: formData
    })
    
    if (response.ok) {
      const result = await response.json()
      console.log('上传成功:', result)
      // 重新加载文档列表
      loadDocuments()
      // 可以添加通知用户上传成功的逻辑
    } else {
      console.error('上传失败:', response.statusText)
      // 可以添加通知用户上传失败的逻辑
    }
  } catch (error) {
    console.error('上传异常:', error)
    // 可以添加通知用户上传异常的逻辑
  }
}

// 选择文件夹
const folderInput = ref(null)

const selectFolder = () => {
  folderInput.value.click()
}

// 处理文件夹选择
const handleFolderChange = async (event) => {
  const files = event.target.files
  if (files.length > 0) {
    console.log('文件夹选择:', files)
    
    // 处理文件夹中的所有文件
    for (const file of files) {
      // 过滤支持的文件类型
      const ext = file.name.split('.').pop().toLowerCase()
      if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext)) {
        try {
          // 创建FormData对象
          const formData = new FormData()
          formData.append('file', file)
          
          // 调用后端上传接口
          const response = await fetch('http://localhost:8013/api/documents/upload', {
            method: 'POST',
            body: formData
          })
          
          if (response.ok) {
            console.log('文件上传成功:', file.name)
          } else {
            console.error('文件上传失败:', file.name, response.statusText)
          }
        } catch (error) {
          console.error('文件上传异常:', file.name, error)
        }
      }
    }
    
    // 重新加载文档列表
    loadDocuments()
    
    // 清空input，以便可以再次选择同一个文件夹
    event.target.value = ''
  }
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
const processDocument = async (document) => {
  console.log('处理文档:', document)
  
  try {
    // 调用后端处理文档接口
    const response = await fetch(`http://localhost:8013/api/documents/${document.id}/process`, {
      method: 'POST'
    })
    
    if (response.ok) {
      const result = await response.json()
      console.log('处理成功:', result)
      // 重新加载文档列表
      loadDocuments()
    } else {
      console.error('处理失败:', response.statusText)
    }
  } catch (error) {
    console.error('处理异常:', error)
  }
}

// 删除文档
const deleteDocument = async (id) => {
  console.log('删除文档:', id)
  
  try {
    // 调用后端删除文档接口
    const response = await fetch(`http://localhost:8013/api/documents/${id}`, {
      method: 'DELETE'
    })
    
    if (response.ok) {
      const result = await response.json()
      console.log('删除成功:', result)
      // 重新加载文档列表
      loadDocuments()
    } else {
      console.error('删除失败:', response.statusText)
    }
  } catch (error) {
    console.error('删除异常:', error)
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
  }
  
  .operation-panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    margin-bottom: 12px;
    flex-shrink: 0;
    
    .search-and-filters {
      display: flex;
      align-items: center;
      gap: 12px;
      
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
      
      .filters {
        display: flex;
        align-items: center;
        gap: 8px;
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
      align-items: flex-start;
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
        margin-top: 2px;
        
        &.file-pdf { background: #e34c26; }
        &.file-doc, &.file-docx { background: #2b5797; }
        &.file-txt { background: #6c757d; }
        &.file-md { background: #007acc; }
      }
      
      .name-container {
        flex: 1;
        min-width: 0;
        
        .name-text {
          font-size: 13px;
          color: #303133;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 300px;
        }
        
        .path-text {
          font-size: 11px;
          color: #909399;
          line-height: 1.2;
          display: block;
          margin-top: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 300px;
        }
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

.upload-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.upload-btn {
  :deep(.el-upload) {
    display: block;
  }
}

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
  gap: 8px;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
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
  gap: 8px;
  
  &:hover {
    background: #ecf5ff;
    border-color: #c6e2ff;
    color: #409eff;
  }
}
</style>