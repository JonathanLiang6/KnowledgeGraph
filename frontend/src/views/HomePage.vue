<template>
  <div class="home-page">
    <!-- Hero — 深色森林 -->
    <section class="hero">
      <div class="hero-glow hero-glow--1" />
      <div class="hero-glow hero-glow--2" />
      <div class="hero-glow hero-glow--3" />
      <div class="hero-inner">
        <div class="hero-logo">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="4" r="3"/>
            <circle cx="5" cy="20" r="3"/>
            <circle cx="19" cy="20" r="3"/>
            <line x1="11" y1="7" x2="6" y2="17"/>
            <line x1="13" y1="7" x2="18" y2="17"/>
          </svg>
        </div>
        <h1>KnowledgeGraph</h1>
        <p class="hero-sub">教学知识图谱 — 文档解析 · 实体抽取 · 图谱可视化 · 智能问答</p>
        <div class="hero-actions">
          <button class="hero-btn hero-btn--primary" @click="openCreateDialog">
            <el-icon :size="18"><Plus /></el-icon>
            新建知识库
          </button>
          <button class="hero-btn hero-btn--ghost" @click="refreshAll">
            <el-icon :size="16"><Refresh /></el-icon>
          </button>
        </div>
        <!-- 三条统计 -->
        <div class="hero-stats">
          <div class="hs-item">
            <span class="hs-val">{{ kbs.length }}</span>
            <span class="hs-label">知识库</span>
          </div>
          <div class="hs-div" />
          <div class="hs-item">
            <span class="hs-val">{{ statsDocCount }}</span>
            <span class="hs-label">文档</span>
          </div>
          <div class="hs-div" />
          <div class="hs-item">
            <span class="hs-val">{{ statsDoneCount }}</span>
            <span class="hs-label">已处理</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 知识库列表 -->
    <section class="content">
      <div class="content-head">
        <h2>我的知识库</h2>
        <span class="content-count" v-if="kbs.length">{{ kbs.length }} 个</span>
      </div>

      <!-- 卡片网格 -->
      <div class="card-grid" v-if="kbs.length">
        <article
          v-for="(kb, idx) in kbs"
          :key="kb.id"
          class="kb-card"
          :style="{ animationDelay: `${idx * 0.07}s` }"
          @click="$router.push(`/kb/${kb.id}/graph`)"
        >
          <div class="kb-card-inner">
            <div class="kbc-top">
              <div class="kbc-icon">
                <el-icon :size="20" color="#fff"><Collection /></el-icon>
              </div>
              <div class="kbc-actions" @click.stop>
                <button class="kbc-act" title="编辑" @click="editKB(kb)"><el-icon :size="14"><Edit /></el-icon></button>
                <button class="kbc-act kbc-act--danger" title="删除" @click="confirmDelete(kb)"><el-icon :size="14"><Delete /></el-icon></button>
              </div>
            </div>
            <h3 class="kbc-name">{{ kb.name }}</h3>
            <p class="kbc-desc">{{ kb.description || '暂无描述' }}</p>
            <div class="kbc-footer">
              <span class="kbc-docs">
                <i class="kbc-dot" />
                {{ kb.document_count || 0 }} 篇文档
              </span>
              <span class="kbc-time">{{ formatDate(kb.updated_at) }}</span>
            </div>
          </div>
        </article>
      </div>

      <!-- 空状态 -->
      <div class="empty-block" v-else-if="!loading">
        <div class="empty-art">
          <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="12" x2="12" y2="18"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <h3>还没有知识库</h3>
        <p>上传教学文档，自动构建知识图谱，探索智能问答</p>
        <button class="hero-btn hero-btn--primary" @click="openCreateDialog">
          <el-icon :size="16"><Plus /></el-icon> 创建第一个
        </button>
      </div>

      <!-- 骨架 -->
      <div class="card-grid" v-else>
        <div v-for="i in 3" :key="i" class="kb-card is-skel">
          <div class="kb-card-inner">
            <div class="skel skel-icon" />
            <div class="skel skel-name" />
            <div class="skel skel-desc" />
            <div class="skel skel-desc short" />
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">KnowledgeGraph v2.5 · 森林绿</footer>

    <!-- 对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingKB ? '编辑知识库' : '新建知识库'"
      width="480px"
      destroy-on-close
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="输入知识库名称" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选描述" maxlength="2000" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '../api/knowledgeBase'
import { Plus, Collection, Edit, Delete, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const kbs = ref([])
const loading = ref(true)
const showCreateDialog = ref(false)
const editingKB = ref(null)
const saving = ref(false)

const form = reactive({ name: '', description: '' })

// 统计：直接从 KB 列表计算，零额外 API
const statsDocCount = computed(() => kbs.value.reduce((s, kb) => s + (kb.document_count || 0), 0))
const statsDoneCount = computed(() => statsDocCount.value) // 简化为总文档数

function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  const now = Date.now()
  const diff = now - dt.getTime()
  if (diff < 3600000) return '刚刚'
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  return dt.toLocaleDateString('zh-CN')
}

async function loadAll() {
  loading.value = true
  try {
    const r = await getKnowledgeBases()
    kbs.value = r.items || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await loadAll()
  ElMessage.success('已刷新')
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
  form.description = kb.description || ''
  showCreateDialog.value = true
}

async function saveKB() {
  const name = form.name.trim()
  if (!name) { ElMessage.warning('请输入名称'); return }
  saving.value = true
  try {
    if (editingKB.value) {
      await updateKnowledgeBase(editingKB.value.id, { name, description: form.description })
      ElMessage.success('已更新')
    } else {
      await createKnowledgeBase({ name, description: form.description })
      ElMessage.success('已创建')
    }
    showCreateDialog.value = false
    editingKB.value = null
    await loadAll()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(kb) {
  try {
    await ElMessageBox.confirm(`删除「${kb.name}」？所有文档将被永久删除。`, '确认删除', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch { /* 用户取消 */ }
}

onMounted(loadAll)
</script>

<style scoped lang="scss">
// ── 基础 ────────────────────────────────────────────
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #E8EFE9; // 更深的底色
}

// ── Hero — 深色森林渐变 ─────────────────────────────
.hero {
  position: relative;
  overflow: hidden;
  padding: 72px 32px 80px;
  text-align: center;
  background: linear-gradient(160deg, #0C2B16 0%, #144D25 30%, #1A5E30 60%, #0D3D1A 100%);
}

.hero-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;

  &--1 {
    width: 400px; height: 400px;
    background: rgba(45, 140, 78, 0.18);
    top: -120px; left: -120px;
    animation: float 10s ease-in-out infinite;
  }
  &--2 {
    width: 320px; height: 320px;
    background: rgba(13, 148, 136, 0.15);
    bottom: -100px; right: -80px;
    animation: float 9s ease-in-out 2s infinite reverse;
  }
  &--3 {
    width: 200px; height: 200px;
    background: rgba(76, 175, 109, 0.12);
    top: 50%; left: 45%;
    transform: translate(-50%, -50%);
    animation: float 7s ease-in-out 1s infinite;
  }
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 640px;
  margin: 0 auto;
}

.hero-logo {
  display: inline-flex;
  width: 76px; height: 76px;
  border-radius: 20px;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.1);
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}

.hero h1 {
  font-size: 34px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.04em;
  margin-bottom: 10px;
}

.hero-sub {
  font-size: 15px;
  color: rgba(255,255,255,0.65);
  margin-bottom: 28px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 40px;
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 12px 28px;
  font-size: 15px;
  font-family: inherit;
  font-weight: 500;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22,1,0.36,1);
  border: none;
  outline: none;

  &--primary {
    background: #fff;
    color: #0F331D;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(0,0,0,0.35);
    }
    &:active { transform: scale(0.97); }
  }

  &--ghost {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.75);
    border: 1px solid rgba(255,255,255,0.12);

    &:hover {
      background: rgba(255,255,255,0.14);
      color: #fff;
    }
  }
}

// ── 统计条 ──────────────────────────────────────────
.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 0;
  background: rgba(0,0,0,0.2);
  backdrop-filter: blur(12px);
  border-radius: 14px;
  padding: 14px 0;
  border: 1px solid rgba(255,255,255,0.06);
}

.hs-item {
  padding: 0 28px;
  text-align: center;
}

.hs-val {
  display: block;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.hs-label {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.hs-div {
  width: 1px; height: 32px;
  background: rgba(255,255,255,0.1);
}

// ── 内容区 ──────────────────────────────────────────
.content {
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 40px 24px 64px;
}

.content-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 24px;

  h2 {
    font-size: 19px;
    font-weight: 600;
    color: #1A2E1F;
  }

  .content-count {
    font-size: 13px;
    color: #7A9A7D;
  }
}

// ── 卡片网格 ────────────────────────────────────────
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 20px;
}

.kb-card {
  animation: fadeInUp 0.5s cubic-bezier(0.22,1,0.36,1) both;
  cursor: pointer;
  transition: transform 0.4s cubic-bezier(0.34,1.56,0.64,1),
              box-shadow 0.4s ease;

  &:hover {
    transform: translateY(-6px);

    .kb-card-inner {
      box-shadow: 0 12px 40px rgba(30,70,40,0.18);
      border-color: rgba(45,140,78,0.35);
    }

    .kbc-actions { opacity: 1; transform: translateY(0); }
  }
}

.kb-card-inner {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #DCE8DE;
  box-shadow: 0 2px 8px rgba(30,50,35,0.05);
  transition: box-shadow 0.4s ease, border-color 0.3s ease;
  position: relative;
  overflow: hidden;

  // 微妙的顶部光条
  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #2D8C4E, #0D9488);
    opacity: 0;
    transition: opacity 0.3s;
  }

  .kb-card:hover &::before {
    opacity: 1;
  }

  .kbc-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .kbc-icon {
    width: 42px; height: 42px;
    border-radius: 12px;
    background: linear-gradient(135deg, #1A5E30, #2D8C4E);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 3px 12px rgba(30,70,40,0.3);
    transition: transform 0.3s ease;

    .kb-card:hover & {
      transform: scale(1.06);
    }
  }

  .kbc-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transform: translateY(-4px);
    transition: all 0.25s ease;
  }

  .kbc-act {
    width: 30px; height: 30px;
    border-radius: 8px;
    border: 1px solid #DCE8DE;
    background: #fff;
    color: #7A9A7D;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;

    &:hover {
      border-color: #2D8C4E;
      color: #2D8C4E;
      background: #F5FAF5;
    }

    &--danger:hover {
      border-color: #E04B4B;
      color: #E04B4B;
      background: #FFF0F0;
    }
  }

  .kbc-name {
    font-size: 17px; font-weight: 600;
    color: #1A2E1F;
    margin-bottom: 8px;
  }

  .kbc-desc {
    font-size: 13px; color: #7A9A7D;
    line-height: 1.5;
    margin-bottom: 16px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 38px;
  }

  .kbc-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px solid #EDF4EE;
  }

  .kbc-docs {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px; color: #8A9A8D;
  }

  .kbc-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #2D8C4E;
    animation: dot-pulse 2.2s ease-in-out infinite;
  }

  .kbc-time {
    font-size: 12px; color: #8A9A8D;
  }
}

// 骨架
.kb-card.is-skel {
  pointer-events: none;
  &:hover { transform: none; }
}

.skel {
  background: linear-gradient(90deg, #E8EFE9 25%, #DFE9E0 50%, #E8EFE9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite;
  border-radius: 6px;

  &.skel-icon { width: 42px; height: 42px; border-radius: 12px; margin-bottom: 16px; }
  &.skel-name { width: 55%; height: 18px; margin-bottom: 8px; }
  &.skel-desc { width: 84%; height: 13px; margin-bottom: 6px; }
  &.short { width: 40%; }
}

// ── 空状态 ──────────────────────────────────────────
.empty-block {
  text-align: center;
  padding: 64px 20px;

  .empty-art {
    display: inline-block;
    color: #2D8C4E;
    opacity: 0.35;
    animation: float 4.5s ease-in-out infinite;
    margin-bottom: 24px;
  }

  h3 { font-size: 18px; font-weight: 600; color: #1A2E1F; margin-bottom: 6px; }
  p { color: #7A9A7D; margin-bottom: 24px; font-size: 14px; }
}

// ── 底部 ────────────────────────────────────────────
.footer {
  text-align: center;
  padding: 24px;
  color: #8A9A8D;
  font-size: 12px;
  border-top: 1px solid #DCE8DE;
  margin-top: auto;
}
</style>
