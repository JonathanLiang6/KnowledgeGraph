<template>
  <div class="topo-root">
    <!-- ====== Hero ====== -->
    <div v-if="showHero" class="hero">
      <div class="hero-bg" />
      <div class="hero-card">
        <img src="/brain.svg" alt="" class="hero-brain" />
        <h1>个人知识库 · 第二大脑</h1>
        <p>文档解析 · 实体抽取 · 图谱可视化 · 智能问答</p>
        <button class="hero-btn" @click="enter">进入我的知识宇宙 →</button>
      </div>
    </div>

    <!-- ====== 图谱画布 ====== -->
    <div v-show="!showHero" class="canvas-shell">
      <div class="topbar">
        <button class="tb-btn tb-green" @click="openCreateKB"><span>＋</span> 新建知识库</button>
        <button class="tb-btn" @click="openCreateNode"><span>📁</span> 新建节点</button>
        <button class="tb-btn" @click="refreshTopo"><span>🔄</span> 刷新</button>
        <button class="tb-btn" @click="showHero = true"><span>🏠</span> 首页</button>
      </div>
      <div class="topbar-hint">单击节点进入知识库 | 右键节点弹出菜单</div>

      <div ref="canvasHost" class="canvas-host" />

      <Teleport to="body">
        <div v-if="menu.show" class="ctx-popup" :style="{ left: menu.x + 'px', top: menu.y + 'px' }" @click.stop>
          <template v-if="menu.node">
            <button class="ctx-btn" @click="menuEnterKB" v-if="menu.node.kb_id">🚀 进入知识库</button>
            <button class="ctx-btn" @click="menuEdit">✏️ 编辑节点</button>
            <button class="ctx-btn ctx-del" @click="menuDelete" v-if="!menu.node.is_root">🗑️ 删除节点</button>
          </template>
          <template v-else>
            <button class="ctx-btn" @click="menuCreate">➕ 在此新建节点</button>
          </template>
        </div>
      </Teleport>
    </div>

    <!-- ====== 节点对话框 ====== -->
    <Teleport to="body">
      <div v-if="dlg.node" class="modal-mask" @click.self="dlg.node = false">
        <div class="modal-box">
          <h3>{{ editingNode ? '编辑节点' : '新建节点' }}</h3>
          <label>名称</label>
          <input v-model="nodeForm.name" class="fld" placeholder="节点名称" maxlength="255" />
          <label>图标 (Emoji)</label>
          <div style="display:flex;align-items:center;gap:8px">
            <input v-model="nodeForm.icon" class="fld" style="width:80px" maxlength="10" />
            <span style="font-size:28px">{{ nodeForm.icon || '📁' }}</span>
          </div>
          <label>绑定知识库</label>
          <select v-model="nodeForm.kb_id" class="fld">
            <option :value="null">-- 不绑定（作为分支节点）--</option>
            <option v-for="kb in kbList" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
          </select>
          <label>父级节点</label>
          <select v-model="nodeForm.parent_id" class="fld">
            <option :value="null">-- 无（独立节点）--</option>
            <option v-for="n in topologyNodes.filter(x => x.id !== editingNode?.id)" :key="n.id" :value="n.id">
              {{ n.is_root ? '⭐' : n.kb_id ? '📚' : '📂' }} {{ n.name }}
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
        <div class="modal-box">
          <h3>新建知识库</h3>
          <label>名称</label>
          <input v-model="kbForm.name" class="fld" placeholder="知识库名称" maxlength="255" />
          <label>描述</label>
          <textarea v-model="kbForm.description" class="fld" rows="3" placeholder="可选描述" />
          <label>父级节点</label>
          <select v-model="kbForm.parent_id" class="fld">
            <option :value="null">-- 选择父节点 --</option>
            <option v-for="n in topologyNodes" :key="n.id" :value="n.id">
              {{ n.is_root ? '⭐' : n.kb_id ? '📚' : '📂' }} {{ n.name }}
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
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { getKnowledgeBases, createKnowledgeBase } from '../api/knowledgeBase'
import { useTopologyRenderer } from '../composables/useTopologyRenderer'

const router = useRouter()
const canvasHost = ref(null)
const showHero = ref(true)
const busy = ref(false)
const busyKb = ref(false)

const topologyNodes = ref([])
const topologyEdges = ref([])
const kbList = ref([])
const editingNode = ref(null)

const nodeForm = reactive({ name: '', icon: '📁', kb_id: null, parent_id: null })
const kbForm = reactive({ name: '', description: '', parent_id: null })
const dlg = reactive({ node: false, kb: false })
const menu = reactive({ show: false, x: 0, y: 0, node: null })

let renderer = null

// ── 生命周期 ──────────────────────────────────────────

onMounted(async () => {
  await loadTopology()
  await loadKBList()
  document.addEventListener('click', onDocClick)
})

onBeforeUnmount(() => {
  if (renderer) renderer.destroy()
  document.removeEventListener('click', onDocClick)
})

function onDocClick() { menu.show = false }

async function loadTopology() {
  try {
    const data = await api.get('/topology')
    topologyNodes.value = data.nodes || []
    topologyEdges.value = data.edges || []
  } catch { topologyNodes.value = []; topologyEdges.value = [] }
}

async function loadKBList() {
  try { const r = await getKnowledgeBases(); kbList.value = r.items || [] } catch {}
}

// ── 进入 / 刷新 ──────────────────────────────────────

async function enter() { showHero.value = false; await nextTick(); await initRenderer() }
async function refreshTopo() { await loadTopology(); await loadKBList(); await initRenderer() }

async function initRenderer() {
  // 只确保根节点存在，不再自动为 KB 创建拓扑节点
  if (!topologyNodes.value.some(n => n.is_root)) {
    try { await api.post('/topology/nodes', { name: '我的知识宇宙', icon: '🧠', kb_id: null }); await loadTopology() } catch {}
  }

  if (renderer) renderer.destroy()

  renderer = useTopologyRenderer(canvasHost, {
    onNodeClick: (node) => {
      menu.show = false
      if (node.kb_id) router.push(`/kb/${node.kb_id}/graph`)
    },
    onNodeDblClick: (node) => {
      if (node.kb_id) router.push(`/kb/${node.kb_id}/graph`)
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

function menuEnterKB() { if (menu.node?.kb_id) router.push(`/kb/${menu.node.kb_id}/graph`); menu.show = false }
function menuEdit() { if (menu.node) openEdit(menu.node); menu.show = false }
async function menuDelete() { menu.show = false; if (menu.node) { editingNode.value = menu.node; await doDelete() } }
function menuCreate() { menu.show = false; openCreateNode() }

// ── 节点编辑 ──────────────────────────────────────────

function openEdit(node) {
  editingNode.value = node
  nodeForm.name = node.name || ''; nodeForm.icon = node.icon || '📁'; nodeForm.kb_id = node.kb_id || null
  const edge = topologyEdges.value.find(e => e.target_id === node.id)
  nodeForm.parent_id = edge ? edge.source_id : null
  dlg.node = true
}

function openCreateNode() {
  editingNode.value = null
  nodeForm.name = ''; nodeForm.icon = '📁'; nodeForm.kb_id = null
  const root = topologyNodes.value.find(n => n.is_root)
  nodeForm.parent_id = root ? root.id : null
  dlg.node = true
}

async function saveNode() {
  const name = nodeForm.name.trim(); if (!name) return ElMessage.warning('请输入名称')
  busy.value = true
  try {
    if (editingNode.value) {
      await api.put(`/topology/nodes/${editingNode.value.id}`, { name, icon: nodeForm.icon || '📁', kb_id: nodeForm.kb_id || null })
      if (nodeForm.parent_id && nodeForm.parent_id !== editingNode.value.id) {
        for (const e of topologyEdges.value.filter(e => e.target_id === editingNode.value.id)) await api.delete(`/topology/edges/${e.id}`).catch(() => {})
        await api.post('/topology/edges', { source_id: nodeForm.parent_id, target_id: editingNode.value.id }).catch(() => {})
      }
      ElMessage.success('已更新')
    } else {
      const node = await api.post('/topology/nodes', { name, icon: nodeForm.icon || '📁', kb_id: nodeForm.kb_id || null })
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
    await ElMessageBox.confirm(`确定删除「${node.name}」？关联的知识库不会删除。`, '确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    busy.value = true
    await api.delete(`/topology/nodes/${node.id}`)
    ElMessage.success('已删除')
    dlg.node = false; editingNode.value = null
    await refreshTopo()
  } catch {} finally { busy.value = false }
}

async function deleteNode() { await doDelete() }

// ── 知识库对话框 ──────────────────────────────────────

function openCreateKB() {
  kbForm.name = ''; kbForm.description = ''
  const root = topologyNodes.value.find(n => n.is_root)
  kbForm.parent_id = root ? root.id : null
  dlg.kb = true
}

async function createKB() {
  const name = kbForm.name.trim(); if (!name) return ElMessage.warning('请输入名称')
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
.topo-root { position:fixed;inset:0;background:#0A1A0E;overflow:hidden;font-family:"PingFang SC","Microsoft YaHei",sans-serif; }

// ── Hero ──────────────────────────────────────────────
.hero { position:absolute;inset:0;z-index:10;display:flex;align-items:center;justify-content:center; }
.hero-bg { position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(30,80,40,0.25),transparent 70%); }
.hero-card { position:relative;text-align:center;max-width:480px;padding:40px; }
.hero-brain { width:120px;height:120px;margin-bottom:16px;opacity:0.85; }
.hero-card h1 { font-size:32px;font-weight:700;color:#fff;margin-bottom:8px; }
.hero-card p { font-size:15px;color:rgba(255,255,255,0.5);margin-bottom:32px; }
.hero-btn {
  display:inline-block;padding:14px 36px;font-size:16px;font-weight:600;font-family:inherit;
  background:linear-gradient(135deg,#2D8C4E,#0D9488);color:#fff;border:none;border-radius:12px;cursor:pointer;
  transition:all 0.3s;box-shadow:0 4px 24px rgba(45,140,78,0.4);
  &:hover { transform:translateY(-2px);box-shadow:0 6px 32px rgba(45,140,78,0.6); }
}

// ── 画布 ──────────────────────────────────────────────
.canvas-shell { position:absolute;inset:0; }
.canvas-host { width:100%;height:100%;canvas{display:block;} }

// ── 工具栏 ────────────────────────────────────────────
.topbar { position:absolute;top:16px;right:16px;z-index:10;display:flex;gap:8px; }
.tb-btn {
  display:inline-flex;align-items:center;gap:4px;padding:7px 14px;font-size:13px;font-family:inherit;
  background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.8);
  border:1px solid rgba(255,255,255,0.12);border-radius:8px;cursor:pointer;transition:all 0.2s;backdrop-filter:blur(8px);
  span { font-size:15px; }
  &:hover { background:rgba(255,255,255,0.14);color:#fff; }
  &.tb-green { border-color:rgba(45,140,78,0.5); }
}
.topbar-hint {
  position:absolute;bottom:20px;left:50%;transform:translateX(-50%);z-index:10;
  padding:5px 16px;font-size:12px;color:rgba(255,255,255,0.35);
  background:rgba(0,0,0,0.35);border-radius:20px;pointer-events:none;
}

// ── 右键菜单 ──────────────────────────────────────────
.ctx-popup {
  position:fixed;z-index:9999;min-width:160px;
  background:#152418;border:1px solid rgba(255,255,255,0.1);border-radius:10px;
  padding:4px 0;box-shadow:0 8px 32px rgba(0,0,0,0.6);
}
.ctx-btn {
  display:block;width:100%;padding:9px 18px;text-align:left;font-size:13px;font-family:inherit;
  background:none;color:rgba(255,255,255,0.85);border:none;cursor:pointer;
  &:hover { background:rgba(45,140,78,0.3); }
  &.ctx-del { color:#f07070;&:hover{background:rgba(200,50,50,0.3)} }
}

// ── 模态对话框 ────────────────────────────────────────
.modal-mask { position:fixed;inset:0;z-index:5000;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center; }
.modal-box {
  background:#1a2a1e;border:1px solid rgba(255,255,255,0.1);border-radius:14px;
  padding:24px;width:440px;max-width:90vw;color:#ddd;
  h3 { font-size:18px;font-weight:600;margin-bottom:20px;color:#fff; }
  label { display:block;font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:4px;margin-top:12px; }
}
.fld {
  width:100%;padding:9px 12px;font-size:14px;font-family:inherit;
  background:rgba(255,255,255,0.06);color:#fff;border:1px solid rgba(255,255,255,0.12);
  border-radius:8px;outline:none;box-sizing:border-box;
  &:focus { border-color:#2D8C4E; }
  option { background:#1a2a1e;color:#fff; }
}
.modal-actions { display:flex;justify-content:space-between;align-items:center;margin-top:24px; }
.btn-primary,.btn-ghost,.btn-danger {
  padding:8px 20px;font-size:14px;font-family:inherit;border-radius:8px;cursor:pointer;border:none;transition:all 0.2s;
}
.btn-primary { background:#2D8C4E;color:#fff;&:hover{background:#3aad5e} }
.btn-ghost { background:rgba(255,255,255,0.08);color:#ccc;border:1px solid rgba(255,255,255,0.12);&:hover{background:rgba(255,255,255,0.15)} }
.btn-danger { background:transparent;color:#e06060;border:1px solid rgba(220,60,60,0.3);&:hover{background:rgba(200,50,50,0.2)} }
</style>
