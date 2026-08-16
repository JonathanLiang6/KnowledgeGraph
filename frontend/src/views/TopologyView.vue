<template>
  <div class="topo-root">
    <!-- ====== Hero ====== -->
    <div v-if="showHero" class="hero">
      <div class="hero-bg" />
      <div class="hero-brain">
        <BrainGraphLogo :size="680" variant="light" />
      </div>
      <div class="hero-content">
        <div class="hero-eyebrow">
          <span class="eyebrow-dot" />
          <span>KNOWLEDGE GRAPH</span>
        </div>
        <h1 class="hero-title">
          <span class="title-line">个人知识库</span>
          <span class="title-line title-light">第二大脑</span>
        </h1>
        <p class="hero-subtitle">
          把文档变成可检索、可推理、可视化的知识网络
        </p>
        <button class="hero-btn" @click="enter">
          进入知识宇宙
          <span class="btn-arrow">→</span>
        </button>
      </div>
    </div>

    <!-- ====== 图谱画布 ====== -->
    <div v-show="!showHero" class="canvas-shell">
      <!-- 左侧可折叠工具栏（居中） -->
      <div class="sidebar-toolbar" :class="{ 'sidebar-toolbar--collapsed': sidebarCollapsed }">
        <div class="sidebar-buttons" v-if="!sidebarCollapsed">
          <button class="sb-btn sb-btn--primary" @click="openCreateKB" title="新建知识库">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span class="sb-label">新建知识库</span>
          </button>
          <button class="sb-btn" @click="openCreateNode" title="新建节点">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" />
            </svg>
            <span class="sb-label">新建节点</span>
          </button>
          <button class="sb-btn" @click="refreshTopo" title="刷新">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span class="sb-label">刷新</span>
          </button>
          <div class="sb-spacer" />
          <button class="sb-btn sb-btn--ghost" @click="showHero = true" title="返回首页">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
            </svg>
            <span class="sb-label">返回首页</span>
          </button>
        </div>
        <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg class="toggle-arrow" :class="{ 'toggle-arrow--expanded': !sidebarCollapsed }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      <div class="topbar-hint">根节点 → 分支节点 → 知识库 · 单击知识库节点进入 · 右键弹出菜单</div>

      <div ref="canvasHost" class="canvas-host" role="application" tabindex="0" aria-label="知识拓扑导航画布：单击知识库节点进入，右键打开操作菜单" />

      <Teleport to="body">
        <div v-if="menu.show" class="ctx-popup" role="menu" :style="{ left: menu.x + 'px', top: menu.y + 'px' }" @click.stop>
          <template v-if="menu.node">
            <div class="ctx-header" v-if="menu.node.name">
              <span class="ctx-header-icon">{{ menu.node.icon || '📂' }}</span>
              <span class="ctx-header-name">{{ menu.node.name }}</span>
            </div>
            <button class="ctx-btn" @click="menuEnterKB" v-if="menu.node.kb_id">
              <span class="ctx-icon">🚀</span><span>进入知识库</span>
              <span class="ctx-shortcut">Enter</span>
            </button>
            <button class="ctx-btn" @click="menuCreateKBHere" v-if="!menu.node.is_root && !menu.node.kb_id">
              <span class="ctx-icon">📚</span><span>在此创建知识库</span>
            </button>
            <button class="ctx-btn" @click="menuEdit">
              <span class="ctx-icon">✏️</span><span>编辑节点</span>
            </button>
            <div class="ctx-sep" v-if="!menu.node.is_root" />
            <button class="ctx-btn ctx-del" @click="menuDelete" v-if="!menu.node.is_root">
              <span class="ctx-icon">🗑️</span><span>删除节点</span>
            </button>
          </template>
          <template v-else>
            <button class="ctx-btn" @click="menuCreate">
              <span class="ctx-icon">➕</span><span>在此新建节点</span>
            </button>
          </template>
        </div>
      </Teleport>
    </div>

    <!-- ====== 节点对话框 ====== -->
    <Teleport to="body">
      <div v-if="dlg.node" class="modal-mask" @click.self="dlg.node = false">
        <div class="modal-box" role="dialog" aria-modal="true">
          <h3>{{ editingNode ? '编辑节点' : '新建节点' }}</h3>
          <label>名称</label>
          <input v-model="nodeForm.name" class="fld" placeholder="节点名称" maxlength="255" />
          <label>图标 (Emoji)</label>
          <div style="display:flex;align-items:center;gap:8px">
            <input v-model="nodeForm.icon" class="fld" style="width:80px" maxlength="10" />
            <span style="font-size:28px">{{ nodeForm.icon || '📂' }}</span>
          </div>
          <template v-if="!editingNode || (!editingNode.is_root && !editingNode.kb_id)">
            <label>绑定知识库</label>
            <select v-model="nodeForm.kb_id" class="fld">
              <option :value="null">-- 不绑定（作为分支节点）--</option>
              <option v-for="kb in kbList" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
            </select>
          </template>
          <label>父级节点</label>
          <select v-model="nodeForm.parent_id" class="fld">
            <option :value="null">-- 无（独立节点）--</option>
            <option v-for="n in topologyNodes.filter(x => x.id !== editingNode?.id && !x.kb_id)" :key="n.id" :value="n.id">
              {{ n.is_root ? '⭐' : '📂' }} {{ n.name }}
            </option>
          </select>
          <div class="modal-actions">
            <button v-if="editingNode && !editingNode.is_root" class="btn-danger" @click="deleteNode" :disabled="busy">删除节点</button>
            <span v-else />
            <div style="display:flex;gap:8px">
              <button class="btn-ghost" @click="dlg.node = false">取消</button>
              <button class="btn-primary" @click="saveNode" :disabled="busy">{{ editingNode ? '保存' : '创建' }}</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ====== 知识库对话框 ====== -->
    <Teleport to="body">
      <div v-if="dlg.kb" class="modal-mask" @click.self="dlg.kb = false">
        <div class="modal-box" role="dialog" aria-modal="true">
          <h3>新建知识库</h3>
          <label>名称</label>
          <input v-model="kbForm.name" class="fld" placeholder="知识库名称" maxlength="255" />
          <label>描述</label>
          <textarea v-model="kbForm.description" class="fld" rows="3" placeholder="可选描述" />
          <label>父级节点（必须为分支节点）</label>
          <select v-model="kbForm.parent_id" class="fld">
            <option :value="null">-- 选择分支节点 --</option>
            <option v-for="n in topologyNodes.filter(x => !x.is_root && !x.kb_id)" :key="n.id" :value="n.id">
              {{ '📂' }} {{ n.name }}
            </option>
          </select>
          <div class="modal-actions">
            <span />
            <div style="display:flex;gap:8px">
              <button class="btn-ghost" @click="dlg.kb = false">取消</button>
              <button class="btn-primary" @click="createKB" :disabled="busyKb">创建</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import BrainGraphLogo from '../components/BrainGraphLogo.vue'
import api from '../api'
import { getKnowledgeBases, createKnowledgeBase } from '../api/knowledgeBase'
import { useTopologyRenderer } from '../composables/useTopologyRenderer'

const router = useRouter()
const pageTransition = inject('pageTransition')
const canvasHost = ref(null)
const showHero = ref(true)
const busy = ref(false)
const busyKb = ref(false)
const sidebarCollapsed = ref(false)

const topologyNodes = ref([])
const topologyEdges = ref([])
const kbList = ref([])
const editingNode = ref(null)

const nodeForm = reactive({ name: '', icon: '📂', kb_id: null, parent_id: null })
const kbForm = reactive({ name: '', description: '', parent_id: null })
const dlg = reactive({ node: false, kb: false })
const menu = reactive({ show: false, x: 0, y: 0, node: null })

let renderer = null

// 监听 nodeForm.kb_id 变化，自动切换图标
watch(() => nodeForm.kb_id, (newKbId) => {
  if (!editingNode.value) {
    // 新建模式：根据是否选择了 kb_id 自动切换图标
    nodeForm.icon = newKbId ? '📚' : '📂'
  }
})

// ── 生命周期 ──────────────────────────────────────────

onMounted(async () => {
  await loadTopology()
  await loadKBList()
  document.addEventListener('click', onDocClick)
  // v4.1 (#70): 页面后台时暂停渲染循环
  document.addEventListener('visibilitychange', handleVisibility)
  // v4.1 (#86): Esc 关闭右键菜单与对话框（键盘可达性）
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  if (renderer) renderer.destroy()
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('visibilitychange', handleVisibility)
  window.removeEventListener('keydown', handleKeydown)
})

function onDocClick() { menu.show = false }

function handleVisibility() {
  if (document.hidden) renderer?.pauseRender?.()
  else if (!showHero.value) renderer?.resumeRender?.()
}

function handleKeydown(e) {
  if (e.key === 'Escape') {
    menu.show = false
    dlg.node = false
    dlg.kb = false
  }
}

// v4.1 (#70): 切回 Hero（画布 v-show 隐藏）时停掉力循环，返回时续跑
watch(showHero, (hero) => {
  if (hero) renderer?.pauseRender?.()
  else renderer?.resumeRender?.()
})

async function loadTopology() {
  try {
    const data = await api.get('/topology')
    topologyNodes.value = data.nodes || []
    topologyEdges.value = data.edges || []
  } catch { topologyNodes.value = []; topologyEdges.value = [] }
}

async function loadKBList() {
  try { const r = await getKnowledgeBases(); kbList.value = r.items || [] } catch { /* 加载失败保持空列表 */ }
}

// ── 进入 / 刷新 ──────────────────────────────────────

async function enter() { showHero.value = false; await nextTick(); await initRenderer() }
async function refreshTopo() { await loadTopology(); await loadKBList(); await initRenderer() }

async function initRenderer() {
  // 只确保根节点存在，不再自动为 KB 创建拓扑节点
  if (!topologyNodes.value.some(n => n.is_root)) {
    try { await api.post('/topology/nodes', { name: '我的知识宇宙', icon: '🧠', kb_id: null }); await loadTopology() } catch { /* 创建失败忽略，稍后重试 */ }
  }

  if (renderer) renderer.destroy()

  renderer = useTopologyRenderer(canvasHost, {
    onNodeClick: (node) => {
      menu.show = false
      if (node.kb_id) {
        goToKB(node)
      } else if (!node.is_root) {
        // 分支节点：高亮选中（后续可扩展展开/收起）
        renderer?.setSelectedNode?.(node.id)
      }
    },
    onNodeDblClick: (node) => {
      if (node.kb_id) goToKB(node)
    },
    onNodeRightClick: (node, sx, sy) => {
      menu.node = node; menu.x = sx; menu.y = sy; menu.show = true
    },
    onCanvasClick: () => { menu.show = false },
    onCanvasRightClick: (sx, sy) => {
      menu.node = null; menu.x = sx; menu.y = sy; menu.show = true
    },
  })
  renderer.init()
  renderer.updateData(topologyNodes.value, topologyEdges.value)
}

// ── 右键菜单回调 ──────────────────────────────────────

function goToKB(node) {
  if (!node?.kb_id) return
  const info = renderer?.getNodeScreenInfo?.(node.id)
  const nodeX = info?.x ?? window.innerWidth / 2
  const nodeY = info?.y ?? window.innerHeight / 2
  const nodeColor = info?.color || '#1E6B40'
  pageTransition?.startNodeExpand(nodeX, nodeY, nodeColor)
  setTimeout(() => {
    router.push(`/kb/${node.kb_id}/graph`)
  }, 550) // 从450ms改为550ms，配合更慢的动画
}

function menuEnterKB() { if (menu.node?.kb_id) goToKB(menu.node); menu.show = false }
function menuEdit() { if (menu.node) openEdit(menu.node); menu.show = false }
function menuCreateKBHere() { if (menu.node) { openCreateKB(menu.node.id) } menu.show = false }
async function menuDelete() { menu.show = false; if (menu.node) { editingNode.value = menu.node; await doDelete() } }
function menuCreate() { menu.show = false; openCreateNode() }

// ── 节点编辑 ──────────────────────────────────────────

function openEdit(node) {
  editingNode.value = node
  nodeForm.name = node.name || ''; nodeForm.icon = node.icon || '📂'; nodeForm.kb_id = node.kb_id || null
  const edge = topologyEdges.value.find(e => e.target_id === node.id)
  nodeForm.parent_id = edge ? edge.source_id : null
  dlg.node = true
}

function openCreateNode() {
  editingNode.value = null
  nodeForm.name = ''; nodeForm.icon = '📂'; nodeForm.kb_id = null
  const root = topologyNodes.value.find(n => n.is_root)
  nodeForm.parent_id = root ? root.id : null
  dlg.node = true
}

async function saveNode() {
  const name = nodeForm.name.trim(); if (!name) return ElMessage.warning('请输入名称')
  // 验证：知识库节点只能挂在分支节点下（三层结构：根→分支→KB）
  if (nodeForm.kb_id && nodeForm.parent_id) {
    const parent = topologyNodes.value.find(n => n.id === nodeForm.parent_id)
    if (!parent || parent.kb_id || parent.is_root) {
      return ElMessage.warning('知识库节点必须放在分支节点下')
    }
  }
  busy.value = true
  try {
    if (editingNode.value) {
      await api.put(`/topology/nodes/${editingNode.value.id}`, { name, icon: nodeForm.icon || '📂', kb_id: nodeForm.kb_id || null })
      if (nodeForm.parent_id && nodeForm.parent_id !== editingNode.value.id) {
        for (const e of topologyEdges.value.filter(e => e.target_id === editingNode.value.id)) await api.delete(`/topology/edges/${e.id}`).catch(() => {})
        await api.post('/topology/edges', { source_id: nodeForm.parent_id, target_id: editingNode.value.id }).catch(() => {})
      }
      ElMessage.success('已更新')
    } else {
      const node = await api.post('/topology/nodes', { name, icon: nodeForm.icon || '📂', kb_id: nodeForm.kb_id || null })
      if (nodeForm.parent_id) await api.post('/topology/edges', { source_id: nodeForm.parent_id, target_id: node.id }).catch(() => {})
      ElMessage.success('已创建')
    }
    dlg.node = false; editingNode.value = null
    await refreshTopo()
  } catch (e) { ElMessage.error(e.message || '操作失败') }
  finally { busy.value = false }
}

async function doDelete() {
  const node = editingNode.value; if (!node || node.is_root) return
  try {
    // 根据节点类型显示不同的确认消息
    let confirmMsg = `确定删除「${node.name}」？`
    if (node.kb_id) {
      confirmMsg += '\n\n⚠️ 此节点绑定了知识库，删除后将级联删除知识库及其所有文档！'
    } else {
      confirmMsg += '\n\n⚠️ 此节点为分支节点，删除后将级联删除其下的所有知识库节点及其知识库！'
    }
    await ElMessageBox.confirm(confirmMsg, '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    busy.value = true
    const result = await api.delete(`/topology/nodes/${node.id}`)
    // 显示详细的删除结果
    if (result.message) {
      ElMessage.success(result.message)
    } else {
      ElMessage.success('已删除')
    }
    dlg.node = false; editingNode.value = null
    await refreshTopo()
  } catch { /* 删除失败已在内部提示 */ } finally { busy.value = false }
}

async function deleteNode() { await doDelete() }

// ── 知识库对话框 ──────────────────────────────────────

function openCreateKB(parentNodeId) {
  kbForm.name = ''; kbForm.description = ''
  if (parentNodeId) {
    // 如果指定了父级（比如从右键菜单触发），直接使用
    kbForm.parent_id = parentNodeId
  } else {
    // 默认选第一个分支节点（知识库必须挂在分支节点下）
    const branchNode = topologyNodes.value.find(n => !n.is_root && !n.kb_id)
    kbForm.parent_id = branchNode ? branchNode.id : null
  }
  dlg.kb = true
}

async function createKB() {
  const name = kbForm.name.trim(); if (!name) return ElMessage.warning('请输入名称')
  if (!kbForm.parent_id) return ElMessage.warning('请选择分支节点作为父级')
  busyKb.value = true
  try {
    const kb = await createKnowledgeBase({ name, description: kbForm.description })
    ElMessage.success('知识库已创建')
    dlg.kb = false
    await loadKBList(); await loadTopology()
    const node = await api.post('/topology/nodes', { name, icon: '📚', kb_id: kb.id })
    if (kbForm.parent_id) await api.post('/topology/edges', { source_id: kbForm.parent_id, target_id: node.id })
    await refreshTopo()
  } catch (e) { ElMessage.error(e.message || '创建失败') }
  finally { busyKb.value = false }
}

// ── 窗口 ──────────────────────────────────────────────

function onResize() { if (renderer) { renderer.resize(); renderer.updateData(topologyNodes.value, topologyEdges.value) } }
watch(showHero, async v => { if (!v) { await nextTick(); window.addEventListener('resize', onResize) } else window.removeEventListener('resize', onResize) })
</script>

<style scoped lang="scss">
.topo-root {
  position: fixed;
  inset: 0;
  background: #050A07;
  overflow: hidden;
  font-family: var(--font-display);
}

// ── Hero ──────────────────────────────────────────────
.hero {
  position: absolute;
  inset: 0;
  z-index: 10;
  overflow: hidden;
  animation: fadeIn 0.8s ease;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 40% 55% at 68% 40%, rgba(58, 157, 91, 0.14), transparent 65%);
}

// 右侧大脑图形
.hero-brain {
  position: absolute;
  bottom: -5%;
  right: -12%;
  opacity: 0.9;
  pointer-events: none;
  animation: brainFloat 6s ease-in-out infinite;

  :deep(.brain-nodes circle) {
    opacity: 0.9;
  }

  :deep(.brain-links line) {
    opacity: 0.6;
  }
}

@keyframes brainFloat {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-8px, -10px); }
}

// 内容区：左侧 + 黄金分割位置
.hero-content {
  position: absolute;
  left: 10%;
  top: 38.2%;
  transform: translateY(-50%);
  max-width: 520px;
  animation: heroIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes heroIn {
  from { opacity: 0; transform: translateY(-40%); }
  to { opacity: 1; transform: translateY(-50%); }
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 28px;

  .eyebrow-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #4CC47E;
  }
}

.hero-title {
  font-size: clamp(44px, 6.5vw, 72px);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.04em;
  color: #FFFFFF;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .title-line {
    display: block;
  }

  .title-light {
    font-weight: 300;
    color: rgba(255, 255, 255, 0.45);
  }
}

.hero-subtitle {
  font-size: 16px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 44px;
  max-width: 420px;
  letter-spacing: 0.01em;
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 13px 26px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  color: #FFFFFF;
  background: #3A9D5B;
  border: 1px solid rgba(76, 196, 126, 0.35);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);

  .btn-arrow {
    transition: transform 0.25s ease;
  }

  &:hover {
    background: #4CAF6D;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(58, 157, 91, 0.4);
    .btn-arrow { transform: translateX(4px); }
  }

  &:active {
    transform: translateY(0);
  }
}

// ── 画布 ──────────────────────────────────────────────
.canvas-shell { position: absolute; inset: 0; }
.canvas-host {
  width: 100%;
  height: 100%;
  canvas { display: block; }
}

// ── 左侧可折叠工具栏（垂直居中） ──────────────────────
.sidebar-toolbar {
  position: absolute;
  top: 50%;
  left: 24px;
  transform: translateY(-50%);
  z-index: 10;
  display: flex;
  align-items: stretch;
  gap: 0;
  padding: 10px 8px;
  background: rgba(20, 36, 24, 0.55);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  transition: all 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
  animation: sidebarIn 0.5s ease 0.3s both;

  &--collapsed {
    padding: 6px;

    .sidebar-buttons { display: none; }
  }
}

@keyframes sidebarIn {
  from { opacity: 0; transform: translate(-12px, -50%); }
  to { opacity: 1; transform: translate(0, -50%); }
}

.sidebar-buttons {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 140px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding-right: 8px;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  padding: 8px 0;
  color: rgba(255, 255, 255, 0.4);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #FFFFFF;
  }

  .toggle-arrow {
    transition: transform 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);

    &--expanded {
      transform: rotate(180deg);
    }
  }
}

.sb-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  background: transparent;
  border: none;
  border-radius: 7px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  svg {
    flex-shrink: 0;
    opacity: 0.7;
  }

  .sb-label {
    transition: opacity 0.2s ease;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #FFFFFF;

    svg { opacity: 1; }
  }

  &--primary {
    background: rgba(58, 157, 91, 0.2);
    color: #FFFFFF;
    &:hover {
      background: rgba(58, 157, 91, 0.35);
    }
  }

  &--ghost {
    margin-top: 4px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding-top: 10px;
  }
}

.sb-spacer {
  flex: 1;
  min-height: 8px;
}

.topbar-hint {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
  letter-spacing: 0.04em;
  pointer-events: none;
  animation: fadeIn 0.6s ease 0.5s both;
}

// ── 右键菜单（克制） ──────────────────────────────────
.ctx-popup {
  position: fixed;
  z-index: 9999;
  min-width: 200px;
  background: rgba(20, 36, 24, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  animation: ctxIn 0.15s ease both;
}

@keyframes ctxIn {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}

.ctx-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px 10px;
  margin-bottom: 2px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .ctx-header-icon { font-size: 15px; }
  .ctx-header-name {
    font-size: 13px;
    font-weight: 500;
    color: #FFFFFF;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.ctx-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 7px 10px;
  font-size: 13px;
  font-family: inherit;
  text-align: left;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;

  .ctx-icon { font-size: 13px; width: 16px; text-align: center; flex-shrink: 0; }
  .ctx-shortcut {
    margin-left: auto;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.25);
    font-family: var(--font-mono);
  }

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #FFFFFF;
  }

  &.ctx-del {
    color: rgba(255, 120, 120, 0.85);
    &:hover {
      background: rgba(220, 60, 60, 0.12);
      color: #FF9090;
    }
  }
}

.ctx-sep {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 4px 8px;
}

// ── 模态对话框（克制） ────────────────────────────────
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 5000;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

.modal-box {
  background: #0F1A12;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 32px;
  width: 440px;
  max-width: 90vw;
  color: rgba(255, 255, 255, 0.7);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
  animation: modalIn 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;

  h3 {
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 24px;
    color: #FFFFFF;
    letter-spacing: -0.01em;
  }

  label {
    display: block;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 6px;
    margin-top: 16px;
    letter-spacing: 0.02em;
  }
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.fld {
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  background: rgba(255, 255, 255, 0.03);
  color: #FFFFFF;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s ease, background 0.15s ease;

  &::placeholder { color: rgba(255, 255, 255, 0.2); }

  &:focus {
    border-color: rgba(60, 182, 110, 0.5);
    background: rgba(255, 255, 255, 0.04);
  }

  option { background: #0F1A12; color: #FFFFFF; }
}

.modal-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 32px;
}

.btn-primary, .btn-ghost, .btn-danger {
  padding: 9px 20px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background: #2D8C4E;
  color: #FFFFFF;
  &:hover { background: #3aad5e; }
  &:active { transform: scale(0.97); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.btn-ghost {
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  &:hover {
    background: rgba(255, 255, 255, 0.04);
    color: #FFFFFF;
  }
}

.btn-danger {
  background: transparent;
  color: rgba(255, 120, 120, 0.8);
  border: 1px solid rgba(220, 60, 60, 0.2);
  &:hover {
    background: rgba(220, 60, 60, 0.1);
    border-color: rgba(220, 60, 60, 0.4);
  }
}

// ── 响应式 ────────────────────────────────────────────
@media (max-width: 768px) {
  .hero-content {
    left: 6%;
    right: 6%;
    top: 35%;
    max-width: none;
  }
  .hero-title { font-size: 42px; }
  .hero-subtitle { font-size: 14px; margin-bottom: 32px; }
  .hero-brain {
    right: -25%;
    bottom: -8%;
    opacity: 0.5;
  }
  .sidebar-toolbar {
    top: 50%;
    left: 16px;
  }
}
</style>
