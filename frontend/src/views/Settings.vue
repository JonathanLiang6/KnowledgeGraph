<template>
  <div class="settings-page">
    <h1 class="page-title">系统设置</h1>

    <div class="settings-grid">
      <!-- 系统参数 -->
      <div class="setting-card card">
        <h3>系统参数</h3>
        <div class="form-row">
          <label>批处理大小</label>
          <el-input-number v-model="form.batch_size" :min="1" :max="100" size="small" />
        </div>
        <div class="form-row">
          <label>文本块大小</label>
          <el-input-number v-model="form.chunk_size" :min="100" :max="5000" :step="100" size="small" />
        </div>
        <div class="form-row">
          <label>重叠比例 {{ (form.overlap_ratio * 100).toFixed(0) }}%</label>
          <el-slider v-model="form.overlap_ratio" :min="0" :max="0.5" :step="0.05" size="small" />
        </div>
        <div class="form-row">
          <label>实体阈值 {{ (form.entity_threshold * 100).toFixed(0) }}%</label>
          <el-slider v-model="form.entity_threshold" :min="0" :max="1" :step="0.05" size="small" />
        </div>
      </div>

      <!-- 视觉设置 -->
      <div class="setting-card card">
        <h3>视觉设置</h3>
        <div class="form-row">
          <label>主色调</label>
          <el-color-picker v-model="form.primary_color" size="small" />
        </div>
        <div class="form-row">
          <label>字号</label>
          <el-select v-model="form.font_size" size="small" style="width: 100%">
            <el-option label="小" value="small" />
            <el-option label="中" value="medium" />
            <el-option label="大" value="large" />
          </el-select>
        </div>
        <div class="form-row">
          <label>启用动画</label>
          <el-switch v-model="form.animations" size="small" />
        </div>
      </div>

      <!-- 系统状态 -->
      <div class="setting-card card">
        <h3>系统状态</h3>
        <div class="status-row">
          <span>API 状态</span>
          <el-tag :type="status.api_configured ? 'success' : 'danger'" size="small">
            {{ status.api_configured ? '已配置' : '未配置' }}
          </el-tag>
        </div>
        <div class="status-row">
          <span>聊天模型</span>
          <span class="text-secondary">{{ status.api_model }}</span>
        </div>
        <div class="status-row">
          <span>嵌入模型</span>
          <span class="text-secondary">{{ status.embedding_model }}</span>
        </div>
        <div class="status-row">
          <span>服务版本</span>
          <span class="text-secondary">v2.0.0</span>
        </div>
      </div>
    </div>

    <!-- 数据统计 -->
    <div class="stats-bar card">
      <div class="stat-item"><strong>{{ stats.documents }}</strong> 文档</div>
      <div class="stat-item"><strong>{{ stats.entities }}</strong> 实体</div>
      <div class="stat-item"><strong>{{ stats.relationships }}</strong> 关系</div>
      <div class="stat-item"><strong>{{ stats.knowledge_bases }}</strong> 知识库</div>
      <div class="stat-item"><strong>{{ stats.storage_used }}</strong> 存储</div>
    </div>

    <!-- 操作 -->
    <div class="actions-bar">
      <button class="btn-primary" @click="saveAll" :disabled="saving">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
      <button class="btn-danger" @click="clearAll">清除所有数据</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getSettings, saveSettings } from '../api/settings'
import { ElMessage, ElMessageBox } from 'element-plus'

const saving = ref(false)
const status = ref({ api_configured: false, api_model: '', embedding_model: '' })
const stats = ref({ documents: 0, entities: 0, relationships: 0, knowledge_bases: 0, storage_used: '0 B' })

const form = reactive({
  batch_size: 5, chunk_size: 1000, overlap_ratio: 0.1,
  entity_threshold: 0.7, relation_threshold: 0.6,
  primary_color: '#4F8CF7', font_size: 'medium', animations: true,
})

async function loadData() {
  try {
    const res = await getSettings()
    if (res.system) Object.assign(form, res.system)
    if (res.visual) Object.assign(form, res.visual)
    status.value = res.system_status || status.value
    stats.value = res.data_stats || stats.value
  } catch {}
}

async function saveAll() {
  saving.value = true
  try {
    await saveSettings({
      system: {
        batch_size: form.batch_size, chunk_size: form.chunk_size,
        overlap_ratio: form.overlap_ratio, entity_threshold: form.entity_threshold,
        relation_threshold: form.relation_threshold,
      },
      visual: {
        primary_color: form.primary_color, font_size: form.font_size,
        animations: form.animations,
      },
    })
    ElMessage.success('设置已保存')
  } catch (e) { ElMessage.error(e.message) }
  saving.value = false
}

function clearAll() {
  ElMessage.info('请在数据库中手动清除')
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.settings-page {
  max-width: 1000px;
  .page-title { margin-bottom: var(--spacing-lg); }
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.setting-card {
  padding: var(--spacing-lg);
  h3 { font-size: 16px; margin-bottom: var(--spacing-md); padding-bottom: var(--spacing-sm); border-bottom: 1px solid var(--border-light); }
  .form-row { margin-bottom: var(--spacing-md);
    label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: var(--spacing-xs); }
  }
}

.status-row {
  display: flex; justify-content: space-between; padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--border-light); font-size: 13px;
  &:last-child { border-bottom: none; }
}

.stats-bar {
  display: flex; gap: var(--spacing-xl); padding: var(--spacing-lg); margin-bottom: var(--spacing-lg);
  .stat-item { font-size: 14px; strong { font-size: 18px; color: var(--color-primary); margin-right: 4px; } }
}

.actions-bar { display: flex; gap: var(--spacing-md); }

.text-secondary { color: var(--text-secondary); }
</style>
