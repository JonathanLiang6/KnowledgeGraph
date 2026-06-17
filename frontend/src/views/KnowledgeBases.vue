<template>
  <div class="knowledge-bases">
    <div class="page-header">
      <h1 class="page-title">知识库管理</h1>
      <button class="btn-primary" @click="showCreateDialog = true">
        <el-icon :size="14"><Plus /></el-icon> 新建知识库
      </button>
    </div>

    <!-- 知识库卡片列表 -->
    <div class="kb-grid" v-if="kbs.length > 0">
      <div v-for="kb in kbs" :key="kb.id" class="kb-card glass-card" @click="$router.push(`/documents?kb_id=${kb.id}`)">
        <div class="kb-card-header">
          <div class="kb-icon">
            <el-icon :size="20" color="#fff"><Collection /></el-icon>
          </div>
          <div class="kb-actions">
            <el-button :icon="Edit" size="small" circle @click.stop="editKB(kb)" />
            <el-button :icon="Delete" size="small" circle type="danger" @click.stop="confirmDelete(kb)" />
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

    <el-empty v-else description="暂无知识库，点击上方按钮创建" />

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="showCreateDialog" :title="editingKB ? '编辑知识库' : '新建知识库'" width="480px">
      <el-form :model="form" label-position="top">
        <el-form-item label="知识库名称" required>
          <el-input v-model="form.name" placeholder="请输入知识库名称" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入知识库描述" maxlength="2000" />
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
import { Plus, Collection, Edit, Delete } from '@element-plus/icons-vue'
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
  } catch {}
}

function editKB(kb) {
  editingKB.value = kb
  form.name = kb.name
  form.description = kb.description
  showCreateDialog.value = true
}

async function saveKB() {
  if (!form.name.trim()) return
  saving.value = true
  try {
    if (editingKB.value) {
      await updateKnowledgeBase(editingKB.value.id, form)
      ElMessage.success('知识库已更新')
    } else {
      await createKnowledgeBase(form)
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
    await ElMessageBox.confirm(`确定要删除知识库「${kb.name}」吗？所有文档将被一并删除。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('知识库已删除')
    await loadKBs()
  } catch {}
}

onMounted(loadKBs)
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.kb-card {
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all var(--transition-normal);

  &:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }

  .kb-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-md);
  }

  .kb-icon {
    width: 40px; height: 40px;
    border-radius: var(--radius-md);
    background: var(--color-primary-gradient);
    display: flex; align-items: center; justify-content: center;
  }

  .kb-name { font-size: 16px; font-weight: 600; margin-bottom: var(--spacing-sm); }
  .kb-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: var(--spacing-md);
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .kb-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-tertiary); }
}
</style>
