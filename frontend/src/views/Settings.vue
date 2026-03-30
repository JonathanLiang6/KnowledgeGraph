<template>
  <div class="settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        系统设置
      </h1>
    </div>

    <!-- 设置选项卡 -->
    <div class="settings-tabs">
      <el-tabs v-model="activeTab" class="tabs-container">
        <el-tab-pane label="API配置" name="api">
          <div class="tab-content">
            <h3 class="section-title">智谱AI API配置</h3>
            <div class="form-card">
              <el-form :model="apiSettings" label-width="120px">
                <el-form-item label="API密钥">
                  <el-input
                    v-model="apiSettings.apiKey"
                    type="password"
                    placeholder="请输入智谱AI API密钥"
                    :show-password="showApiKey"
                  >
                    <template #append>
                      <el-button @click="showApiKey = !showApiKey" type="text">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path v-if="!showApiKey" d="M9.88 9.88a3 3 0 1 0 4.24 4.24"></path>
                            <path v-if="!showApiKey" d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"></path>
                            <path v-if="!showApiKey" d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"></path>
                            <line v-if="!showApiKey" x1="2" y1="2" x2="22" y2="22"></line>
                            <path v-else d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z"></path>
                            <circle v-if="showApiKey" cx="12" cy="12" r="3"></circle>
                          </svg>
                      </el-button>
                    </template>
                  </el-input>
                  <div class="form-hint">获取API密钥：<a href="https://open.bigmodel.cn/" target="_blank">智谱AI开放平台</a></div>
                </el-form-item>
                <el-form-item label="API基础URL">
                  <el-input
                    v-model="apiSettings.apiBaseUrl"
                    placeholder="请输入API基础URL"
                  ></el-input>
                </el-form-item>
                <el-form-item label="模型选择">
                  <el-select v-model="apiSettings.model" placeholder="选择模型">
                    <el-option label="GLM-4" value="glm-4"></el-option>
                    <el-option label="GLM-3.5" value="glm-3.5"></el-option>
                    <el-option label="GLM-3" value="glm-3"></el-option>
                  </el-select>
                </el-form-item>
                <el-form-item label="请求超时">
                  <el-input-number
                    v-model="apiSettings.timeout"
                    :min="1"
                    :max="600"
                    :step="1"
                    suffix="秒"
                  ></el-input-number>
                </el-form-item>
                <el-form-item>
                  <button class="btn-primary" @click="saveApiSettings">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                      <polyline points="17 21 17 13 7 13 7 21"></polyline>
                      <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    保存配置
                  </button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="系统参数" name="system">
          <div class="tab-content">
            <h3 class="section-title">处理参数配置</h3>
            <div class="form-card">
              <el-form :model="systemSettings" label-width="150px">
                <el-form-item label="批处理大小">
                  <el-input-number
                    v-model="systemSettings.batchSize"
                    :min="1"
                    :max="100"
                    :step="1"
                  ></el-input-number>
                  <div class="form-hint">每批处理的文档数量</div>
                </el-form-item>
                <el-form-item label="文本块大小">
                  <el-input-number
                    v-model="systemSettings.chunkSize"
                    :min="100"
                    :max="5000"
                    :step="100"
                  ></el-input-number>
                  <div class="form-hint">文本分块的大小（字符数）</div>
                </el-form-item>
                <el-form-item label="重叠比例">
                  <el-slider
                    v-model="systemSettings.overlapRatio"
                    :min="0"
                    :max="0.5"
                    :step="0.05"
                  ></el-slider>
                  <div class="form-hint">{{ systemSettings.overlapRatio * 100 }}% 的文本块重叠</div>
                </el-form-item>
                <el-form-item label="实体提取阈值">
                  <el-slider
                    v-model="systemSettings.entityThreshold"
                    :min="0"
                    :max="1"
                    :step="0.01"
                  ></el-slider>
                  <div class="form-hint">{{ (systemSettings.entityThreshold * 100).toFixed(1) }}% 的置信度阈值</div>
                </el-form-item>
                <el-form-item label="关系提取阈值">
                  <el-slider
                    v-model="systemSettings.relationThreshold"
                    :min="0"
                    :max="1"
                    :step="0.01"
                  ></el-slider>
                  <div class="form-hint">{{ (systemSettings.relationThreshold * 100).toFixed(1) }}% 的置信度阈值</div>
                </el-form-item>
                <el-form-item>
                  <button class="btn-primary" @click="saveSystemSettings">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                      <polyline points="17 21 17 13 7 13 7 21"></polyline>
                      <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    保存配置
                  </button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="视觉设置" name="visual">
          <div class="tab-content">
            <h3 class="section-title">界面外观配置</h3>
            <div class="form-card">
              <el-form :model="visualSettings" label-width="120px">
                <el-form-item label="主题选择">
                  <el-radio-group v-model="visualSettings.theme">
                    <el-radio-button label="light">浅色</el-radio-button>
                    <el-radio-button label="dark">深色</el-radio-button>
                    <el-radio-button label="auto">自动</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="主色调">
                  <el-color-picker v-model="visualSettings.primaryColor"></el-color-picker>
                </el-form-item>
                <el-form-item label="字体大小">
                  <el-select v-model="visualSettings.fontSize">
                    <el-option label="小" value="small"></el-option>
                    <el-option label="中" value="medium"></el-option>
                    <el-option label="大" value="large"></el-option>
                  </el-select>
                </el-form-item>
                <el-form-item label="动画效果">
                  <el-switch v-model="visualSettings.animations"></el-switch>
                </el-form-item>
                <el-form-item>
                  <button class="btn-primary" @click="saveVisualSettings">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                      <polyline points="17 21 17 13 7 13 7 21"></polyline>
                      <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    保存配置
                  </button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="数据管理" name="data">
          <div class="tab-content">
            <h3 class="section-title">数据管理</h3>
            <div class="form-card">
              <div class="data-stats">
                <div class="stat-item">
                  <div class="stat-value">{{ dataStats.documents }}</div>
                  <div class="stat-label">文档数量</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value">{{ dataStats.entities }}</div>
                  <div class="stat-label">实体数量</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value">{{ dataStats.relationships }}</div>
                  <div class="stat-label">关系数量</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value">{{ dataStats.storageUsed }}</div>
                  <div class="stat-label">存储使用</div>
                </div>
              </div>
              
              <div class="data-actions">
                <h4>数据操作</h4>
                <button class="btn-secondary" @click="clearCache">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 6h18"></path>
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                  </svg>
                  清除缓存
                </button>
                <button class="btn-secondary" @click="exportData">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  导出数据
                </button>
                <button class="btn-danger" @click="confirmClearAll">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                  清空所有数据
                </button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="关于" name="about">
          <div class="tab-content">
            <div class="about-card">
              <div class="about-header">
                <div class="logo">
                  <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                  </svg>
                </div>
                <h2>知识图谱系统</h2>
                <p class="version">版本 1.0.0</p>
              </div>
              <div class="about-content">
                <p>基于GraphRAG技术的知识图谱系统，使用智谱AI进行实体和关系提取，Neo4j作为图数据库存储。</p>
                <div class="tech-stack">
                  <h3>技术栈</h3>
                  <div class="stack-list">
                    <span class="stack-item">Vue 3</span>
                    <span class="stack-item">Element Plus</span>
                    <span class="stack-item">D3.js</span>
                    <span class="stack-item">FastAPI</span>
                    <span class="stack-item">Neo4j</span>
                    <span class="stack-item">智谱AI</span>
                  </div>
                </div>
                <div class="copyright">
                  <p>© 2026 知识图谱系统. 保留所有权利.</p>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 确认对话框 -->
    <el-dialog
      v-model="confirmDialogVisible"
      title="确认操作"
      width="400px"
    >
      <p>{{ confirmMessage }}</p>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="confirmDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="handleConfirmAction">确认</el-button>
        </span>
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

// 显示消息
const showMessage = (message) => {
  // 这里可以使用Element Plus的消息组件
  console.log(message)
}
</script>

<style scoped>
.settings {
  .page-header {
    margin-bottom: 32px;
    
    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .settings-tabs {
    .tabs-container {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      overflow: hidden;
      
      .el-tabs__header {
        border-bottom: 1px solid #f0f2f5;
        
        .el-tabs__nav {
          margin: 0 20px;
        }
        
        .el-tabs__item {
          font-size: 14px;
          font-weight: 500;
          padding: 16px 20px;
          
          &.is-active {
            color: #667eea;
          }
        }
        
        .el-tabs__active-bar {
          background: #667eea;
        }
      }
      
      .el-tabs__content {
        padding: 24px;
      }
    }
  }

  .tab-content {
    .section-title {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 20px;
    }
    
    .form-card {
      background: #fafafa;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 24px;
      
      .form-hint {
        font-size: 12px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }

  .data-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
    
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

  .data-actions {
    h4 {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 16px;
    }
    
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .about-card {
    background: #fafafa;
    border-radius: 12px;
    padding: 32px;
    text-align: center;
    
    .about-header {
      margin-bottom: 32px;
      
      .logo {
        margin-bottom: 16px;
        color: #667eea;
      }
      
      h2 {
        font-size: 24px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 8px;
      }
      
      .version {
        font-size: 14px;
        color: #909399;
      }
    }
    
    .about-content {
      p {
        font-size: 14px;
        color: #606266;
        line-height: 1.6;
        margin-bottom: 24px;
      }
      
      .tech-stack {
        margin-bottom: 24px;
        
        h3 {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin-bottom: 16px;
        }
        
        .stack-list {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 8px;
          
          .stack-item {
            background: white;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            color: #667eea;
            border: 1px solid #e1e5e9;
          }
        }
      }
      
      .copyright {
        font-size: 12px;
        color: #909399;
        border-top: 1px solid #e1e5e9;
        padding-top: 16px;
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
}

/* 响应式设计 */
@media (max-width: 768px) {
  .settings {
    .settings-tabs {
      .tabs-container {
        .el-tabs__header {
          .el-tabs__nav {
            margin: 0 10px;
          }
          
          .el-tabs__item {
            padding: 12px 10px;
            font-size: 12px;
          }
        }
        
        .el-tabs__content {
          padding: 16px;
        }
      }
    }
    
    .tab-content {
      .form-card {
        padding: 16px;
      }
    }
    
    .data-stats {
      grid-template-columns: repeat(2, 1fr);
    }
    
    .data-actions {
      flex-direction: column;
      
      button {
        width: 100%;
      }
    }
  }
}
</style>