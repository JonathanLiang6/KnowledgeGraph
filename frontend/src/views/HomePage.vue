<template>
  <div class="home-page">
    <!-- 顶部 -->
    <header class="home-header">
      <div class="logo" @click="$router.push('/')">
        <div class="logo-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
            <line x1="12" y1="7" x2="5" y2="17"/><line x1="12" y1="7" x2="19" y2="17"/>
            <line x1="5" y1="17" x2="19" y2="17"/>
          </svg>
        </div>
        <span class="logo-text">KnowledgeGraph</span>
      </div>
    </header>

    <main class="home-main">
      <!-- 标题区域 -->
      <div class="hero">
        <h1>知识库管理</h1>
        <p>创建和管理你的教学知识库，构建知识图谱，开启智能问答</p>
        <button class="btn-primary btn-lg" @click="openCreateDialog">
          <el-icon :size="16"><Plus /></el-icon> 新建知识库
        </button>
      </div>

      <!-- 知识库卡片网格 -->
      <div class="kb-grid" v-if="kbs.length > 0">
        <div
          v-for="kb in kbs"
          :key="kb.id"
          class="kb-card glass-card"
          @click="$router.push(`/kb/${kb.id}/graph`)"
        >
          <div class="kb-card-header">
            <div class="kb-icon">
              <el-icon :size="20" color="#fff"><Collection /></el-icon>
            </div>
            <div class="kb-actions" @click.stop>
              <el-button :icon="Edit" size="small" circle @click="editKB(kb)" />
              <el-button :icon="Delete" size="small" circle type="danger" @click="confirmDelete(kb)" />
            </div>
          </div>
          <h3 class="kb-name">{{ kb.name }}</h3>
          <p class="kb-desc">{{ kb.description || '暂无描述' }}</p>
          <div class="kb-meta">
            <span>{{ kb.document_count }} 篇文档</span>
            <span>{{ formatDate(kb.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-else>
        <el-icon :size="64" color="var(--text-tertiary)"><FolderOpened /></el-icon>
        <p>暂无知识库</p>
        <span>点击上方按钮创建第一个知识库</span>
      </div>
    </main>

    <!-- 底部 -->
    <footer class="home-footer">
      <span>KnowledgeGraph v2.0 · 教学知识图谱管理后台</span>
    </footer>

    <!-- 创建 / 编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingKB ? '编辑知识库' : '新建知识库'"
      width="480px"
      destroy-on-close
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="知识库名称" required>
          <el-input v-model="form.name" placeholder="请输入知识库名称" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述（可选）"
            maxlength="2000"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveKB" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '../api/knowledgeBase'
import { Plus, Collection, Edit, Delete, FolderOpened } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const kbs = ref([])
const showCreateDialog = ref(false)
const editingKB = ref(null)
const saving = ref(false)

const form = reactive({ name: '', description: '' })

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

async function loadKBs() {
  try {
    const res = await getKnowledgeBases()
    kbs.value = res.items || []
  } catch (e) {
    console.error('加载知识库列表失败:', e)
    ElMessage.error('加载知识库列表失败')
  }
}

function openCreateDialog() {
  editingKB.value = null
  form.name = ''
  form.description = ''
  showCreateDialog.value = true
}

function editKB(kb) {
  editingKB.value = kb
  form.name = kb.name
  form.description = kb.description
  showCreateDialog.value = true
}

async function saveKB() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  saving.value = true
  try {
    if (editingKB.value) {
      await updateKnowledgeBase(editingKB.value.id, {
        name: form.name,
        description: form.description,
      })
      ElMessage.success('知识库已更新')
    } else {
      await createKnowledgeBase({
        name: form.name,
        description: form.description,
      })
      ElMessage.success('知识库已创建')
    }
    showCreateDialog.value = false
    editingKB.value = null
    form.name = ''
    form.description = ''
    await loadKBs()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(kb) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${kb.name}」吗？所有文档将被一并删除。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      }
    )
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('知识库已删除')
    await loadKBs()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      console.error('删除知识库失败:', e)
    }
  }
}

onMounted(loadKBs)
</script>

<style scoped lang="scss">
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
}

.home-header {
  display: flex;
  align-items: center;
  padding: 16px 32px;
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 50;

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    user-select: none;

    .logo-icon {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-md);
      background: var(--color-primary-gradient);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .logo-text {
      font-size: 16px;
      font-weight: 700;
      background: var(--color-primary-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }
}

.home-main {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: var(--spacing-xl) var(--spacing-lg);
}

.hero {
  text-align: center;
  padding: 40px 20px 48px;

  h1 {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--spacing-sm);
    letter-spacing: -0.02em;
  }

  p {
    color: var(--text-secondary);
    font-size: 15px;
    margin-bottom: var(--spacing-lg);
  }
}

.btn-lg {
  padding: 10px 24px;
  font-size: 15px;
  border-radius: var(--radius-md);
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
}

.kb-card {
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all var(--transition-normal);

  &:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
  }

  .kb-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-md);
  }

  .kb-icon {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-md);
    background: var(--color-primary-gradient);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .kb-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity var(--transition-fast);
  }

  &:hover .kb-actions {
    opacity: 1;
  }

  .kb-name {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
    color: var(--text-primary);
  }

  .kb-desc {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-md);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 36px;
  }

  .kb-meta {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-tertiary);

  p {
    font-size: 16px;
    margin-top: var(--spacing-md);
    margin-bottom: var(--spacing-xs);
  }

  span {
    font-size: 13px;
  }
}

.home-footer {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-tertiary);
  font-size: 12px;
  border-top: 1px solid var(--border-light);
}
</style>
