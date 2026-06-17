<template>
  <div class="dashboard">
    <h1 class="page-title">仪表盘概览</h1>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card glass-card">
        <div class="stat-icon" style="background: var(--color-primary-gradient);">
          <el-icon :size="22" color="#fff"><Document /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.documents }}</span>
          <span class="stat-label">文档总数</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #5C6BC0, #AB47BC);">
          <el-icon :size="22" color="#fff"><Share /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.entities }}</span>
          <span class="stat-label">知识实体</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #26A69A, #66BB6A);">
          <el-icon :size="22" color="#fff"><Connection /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.relationships }}</span>
          <span class="stat-label">实体关系</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #29B6F6, #42A5F5);">
          <el-icon :size="22" color="#fff"><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.knowledge_bases }}</span>
          <span class="stat-label">知识库</span>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <h3>快速操作</h3>
      <div class="actions-row">
        <button class="action-card card" @click="$router.push('/knowledge-bases')">
          <el-icon :size="24"><Plus /></el-icon>
          <span>新建知识库</span>
        </button>
        <button class="action-card card" @click="$router.push('/documents')">
          <el-icon :size="24"><Upload /></el-icon>
          <span>上传文档</span>
        </button>
        <button class="action-card card" @click="$router.push('/chat')">
          <el-icon :size="24"><ChatDotRound /></el-icon>
          <span>开始问答</span>
        </button>
        <button class="action-card card" @click="$router.push('/graph')">
          <el-icon :size="24"><Share /></el-icon>
          <span>探索图谱</span>
        </button>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="system-status card">
      <h3>系统状态</h3>
      <div class="status-info">
        <span>API 状态</span>
        <el-tag :type="apiConfigured ? 'success' : 'danger'" size="small">
          {{ apiConfigured ? '已配置' : '未配置' }}
        </el-tag>
      </div>
      <div class="status-info">
        <span>模型</span>
        <span class="text-secondary">{{ apiModel }}</span>
      </div>
      <div class="status-info">
        <span>版本</span>
        <span class="text-secondary">v2.0.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings } from '../api/settings'
import { Document, Share, Connection, Collection, Plus, Upload, ChatDotRound } from '@element-plus/icons-vue'

const stats = ref({ documents: 0, entities: 0, relationships: 0, knowledge_bases: 0 })
const apiConfigured = ref(false)
const apiModel = ref('')

onMounted(async () => {
  try {
    const res = await getSettings()
    stats.value = res.data_stats || stats.value
    apiConfigured.value = res.system_status?.api_configured || false
    apiModel.value = res.system_status?.api_model || ''
  } catch {}
})
</script>

<style scoped lang="scss">
.dashboard {
  max-width: 1200px;

  .page-title { margin-bottom: var(--spacing-lg); }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .stat-info {
    display: flex;
    flex-direction: column;
    .stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); }
    .stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  }
}

.quick-actions {
  margin-bottom: var(--spacing-lg);
  h3 { margin-bottom: var(--spacing-md); font-size: 16px; }

  .actions-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
  }

  .action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-lg);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    cursor: pointer;
    color: var(--color-primary);
    transition: all var(--transition-normal);

    &:hover {
      border-color: var(--color-primary-light);
      box-shadow: var(--shadow-md);
      transform: translateY(-2px);
    }
  }
}

.system-status {
  padding: var(--spacing-lg);
  h3 { margin-bottom: var(--spacing-md); font-size: 16px; }

  .status-info {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-light);
    &:last-child { border-bottom: none; }
  }
}

.text-secondary { color: var(--text-secondary); }

@media (max-width: 1024px) {
  .stats-grid, .quick-actions .actions-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
