<template>
  <div class="settings">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        系统设置
      </h1>
      
      <button class="btn-primary btn-sm" @click="saveAllSettings">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
        </svg>
        保存设置
      </button>
    </div>

    <!-- 设置内容 - 两列布局 -->
    <div class="settings-content">
      <!-- 左侧：API配置 -->
      <div class="settings-panel">
        <div class="panel-header">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
          </svg>
          <h3>API配置</h3>
        </div>
        <div class="panel-body">
          <div class="form-row">
            <label>API密钥</label>
            <el-input
              v-model="apiSettings.apiKey"
              type="password"
              placeholder="请输入API密钥"
              size="small"
              show-password
            />
          </div>
          <div class="form-row">
            <label>API地址</label>
            <el-input
              v-model="apiSettings.apiBaseUrl"
              placeholder="https://open.bigmodel.cn/api/paas/v4"
              size="small"
            />
          </div>
          <div class="form-row">
            <label>模型</label>
            <el-select v-model="apiSettings.model" size="small" style="width: 100%">
              <el-option label="GLM-4-Air" value="glm-4-air"></el-option>
              <el-option label="GLM-4" value="glm-4"></el-option>
              <el-option label="GLM-3.5" value="glm-3.5"></el-option>
            </el-select>
          </div>
          <div class="form-row">
            <label>超时(秒)</label>
            <el-input-number v-model="apiSettings.timeout" :min="1" :max="300" size="small" style="width: 100%" />
          </div>
        </div>
      </div>

      <!-- 右侧：系统参数 -->
      <div class="settings-panel">
        <div class="panel-header">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <h3>系统参数</h3>
        </div>
        <div class="panel-body">
          <div class="form-row">
            <label>批处理大小</label>
            <el-input-number v-model="systemSettings.batchSize" :min="1" :max="100" size="small" style="width: 100%" />
          </div>
          <div class="form-row">
            <label>文本块大小</label>
            <el-input-number v-model="systemSettings.chunkSize" :min="100" :max="5000" :step="100" size="small" style="width: 100%" />
          </div>
          <div class="form-row">
            <label>重叠比例 {{ (systemSettings.overlapRatio * 100).toFixed(0) }}%</label>
            <el-slider v-model="systemSettings.overlapRatio" :min="0" :max="0.5" :step="0.05" size="small" />
          </div>
          <div class="form-row">
            <label>实体阈值 {{ (systemSettings.entityThreshold * 100).toFixed(0) }}%</label>
            <el-slider v-model="systemSettings.entityThreshold" :min="0" :max="1" :step="0.05" size="small" />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：数据统计和操作 -->
    <div class="settings-footer">
      <div class="stats-section">
        <div class="stat-item">
          <div class="stat-value">{{ dataStats.documents }}</div>
          <div class="stat-label">文档</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ dataStats.entities }}</div>
          <div class="stat-label">实体</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ dataStats.relationships }}</div>
          <div class="stat-label">关系</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ dataStats.storageUsed }}</div>
          <div class="stat-label">存储</div>
        </div>
      </div>
      
      <div class="actions-section">
        <button class="btn-secondary btn-sm" @click="clearCache">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18"></path>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
          </svg>
          清除缓存
        </button>
        <button class="btn-secondary btn-sm" @click="exportData">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
          </svg>
          导出
        </button>
        <button class="btn-danger btn-sm" @click="confirmClearAll">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
          </svg>
          清空
        </button>
      </div>
    </div>

    <!-- 确认对话框 -->
    <el-dialog v-model="confirmDialogVisible" title="确认操作" width="400px">
      <p>{{ confirmMessage }}</p>
      <template #footer>
        <el-button @click="confirmDialogVisible = false" size="small">取消</el-button>
        <el-button type="danger" @click="handleConfirmAction" size="small">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

// 激活的选项卡
const activeTab = ref('api')

// API配置
const showApiKey = ref(false)
const apiSettings = reactive({
  apiKey: '',
  apiBaseUrl: 'https://open.bigmodel.cn/api/messages',
  model: 'glm-4',
  timeout: 30
})

// 系统参数
const systemSettings = reactive({
  batchSize: 5,
  chunkSize: 1000,
  overlapRatio: 0.1,
  entityThreshold: 0.7,
  relationThreshold: 0.6
})

// 视觉设置
const visualSettings = reactive({
  theme: 'light',
  primaryColor: '#667eea',
  fontSize: 'medium',
  animations: true
})

// 数据统计
const dataStats = reactive({
  documents: 12,
  entities: 1568,
  relationships: 2890,
  storageUsed: '128 MB'
})

// 确认对话框
const confirmDialogVisible = ref(false)
const confirmMessage = ref('')
let confirmAction = null

// 保存API配置
const saveApiSettings = () => {
  console.log('保存API配置:', apiSettings)
  // 这里可以添加保存逻辑
  showMessage('API配置保存成功')
}

// 保存系统配置
const saveSystemSettings = () => {
  console.log('保存系统配置:', systemSettings)
  // 这里可以添加保存逻辑
  showMessage('系统配置保存成功')
}

// 保存视觉配置
const saveVisualSettings = () => {
  console.log('保存视觉配置:', visualSettings)
  // 这里可以添加保存逻辑
  showMessage('视觉配置保存成功')
}

// 清除缓存
const clearCache = () => {
  confirmMessage.value = '确定要清除缓存吗？这将删除临时数据，但不会影响已处理的文档和知识图谱。'
  confirmAction = () => {
    console.log('清除缓存')
    // 这里可以添加清除缓存逻辑
    showMessage('缓存已清除')
  }
  confirmDialogVisible.value = true
}

// 导出数据
const exportData = () => {
  console.log('导出数据')
  // 这里可以添加导出数据逻辑
  showMessage('数据导出功能开发中')
}

// 确认清空所有数据
const confirmClearAll = () => {
  confirmMessage.value = '确定要清空所有数据吗？这将删除所有文档、实体和关系，操作不可恢复！'
  confirmAction = () => {
    console.log('清空所有数据')
    // 这里可以添加清空数据逻辑
    showMessage('所有数据已清空')
  }
  confirmDialogVisible.value = true
}

// 处理确认操作
const handleConfirmAction = () => {
  if (confirmAction) {
    confirmAction()
  }
  confirmDialogVisible.value = false
  confirmAction = null
}

// 保存所有设置
const saveAllSettings = () => {
  console.log('保存所有设置:', { apiSettings, systemSettings, visualSettings })
  // 这里可以添加保存逻辑
  showMessage('所有设置保存成功')
}

// 显示消息
const showMessage = (message) => {
  // 这里可以使用Element Plus的消息组件
  console.log(message)
}
</script>

<style scoped>
.settings {
  height: 100%;
  display: flex;
  flex-direction: column;
  
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 0 16px 0;
    border-bottom: 1px solid #f0f2f5;
    margin-bottom: 20px;
    
    .page-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .settings-content {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
    overflow: hidden;
    
    .settings-panel {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      overflow: hidden;
      
      .panel-header {
        background: #f5f7fa;
        padding: 16px 20px;
        border-bottom: 1px solid #f0f2f5;
        display: flex;
        align-items: center;
        gap: 8px;
        
        h3 {
          font-size: 14px;
          font-weight: 600;
          color: #303133;
          margin: 0;
        }
      }
      
      .panel-body {
        padding: 20px;
        
        .form-row {
          margin-bottom: 16px;
          
          label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #606266;
            margin-bottom: 8px;
          }
        }
      }
    }
  }

  .settings-footer {
    border-top: 1px solid #f0f2f5;
    padding-top: 16px;
    
    .stats-section {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 16px;
      
      .stat-item {
        background: white;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        
        .stat-value {
          font-size: 18px;
          font-weight: 700;
          color: #667eea;
          margin-bottom: 4px;
        }
        
        .stat-label {
          font-size: 11px;
          color: #909399;
        }
      }
    }
    
    .actions-section {
      display: flex;
      gap: 10px;
      justify-content: flex-end;
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
  
  &.btn-sm {
    padding: 8px 12px;
    font-size: 12px;
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
  
  &.btn-sm {
    padding: 8px 12px;
    font-size: 12px;
  }
}

.btn-danger {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
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
    background: #fde2e2;
    border-color: #f9a8a8;
    color: #f56c6c;
  }
  
  &.btn-sm {
    padding: 8px 12px;
    font-size: 12px;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .settings {
    .settings-content {
      grid-template-columns: 1fr;
      gap: 16px;
    }
    
    .settings-footer {
      .stats-section {
        grid-template-columns: repeat(2, 1fr);
      }
      
      .actions-section {
        flex-direction: column;
        
        button {
          width: 100%;
        }
      }
    }
  }
}
</style>