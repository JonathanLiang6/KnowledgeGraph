<template>
  <div class="graph-workspace">
    <div class="graph-toolbar">
      <h1 class="page-title">图谱工作台</h1>
      <div class="toolbar-actions">
        <el-select v-model="layoutMode" size="small" style="width: 120px" @change="changeLayout">
          <el-option label="力导向" value="force" />
          <el-option label="环形" value="circle" />
          <el-option label="树形" value="tree" />
          <el-option label="网格" value="grid" />
        </el-select>
        <button class="btn-secondary" @click="zoomIn">放大</button>
        <button class="btn-secondary" @click="zoomOut">缩小</button>
        <button class="btn-secondary" @click="resetView">重置</button>
        <button class="btn-primary" @click="refreshData">刷新数据</button>
      </div>
    </div>

    <div class="graph-main">
      <canvas ref="canvasRef" class="graph-canvas" @click="onCanvasClick" />

      <!-- 图例 -->
      <div class="legend-panel glass-card" v-if="legend && Object.keys(legend).length > 0">
        <h4>图例</h4>
        <div v-for="(color, type) in legend" :key="type" class="legend-item">
          <span class="legend-dot" :style="{ background: color }" />
          <span>{{ type }}</span>
        </div>
      </div>

      <!-- 统计 -->
      <div class="stats-panel glass-card">
        <h4>图谱统计</h4>
        <div class="stat-row"><span>节点数</span><strong>{{ nodeCount }}</strong></div>
        <div class="stat-row"><span>边数</span><strong>{{ linkCount }}</strong></div>
      </div>
    </div>

    <!-- 实体详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="实体详情" size="360px">
      <div v-if="selectedEntity">
        <h3>{{ selectedEntity.name }}</h3>
        <p class="entity-type"><el-tag size="small">{{ selectedEntity.type }}</el-tag></p>
        <p>权重: {{ selectedEntity.weight?.toFixed(3) }}</p>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef, markRaw } from 'vue'
import { useGraphRenderer } from '../composables/useGraphRenderer'
import { getGraphData } from '../api/graph'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()
const canvasRef = ref(null)
const layoutMode = ref('force')
const legend = ref({})
const nodeCount = ref(0)
const linkCount = ref(0)
const selectedEntity = ref(null)
const drawerVisible = ref(false)
const graphWidth = ref(1200)
const graphHeight = ref(700)

let renderer = null

async function refreshData() {
  try {
    const res = await getGraphData({ kb_id: appStore.currentKB?.id, limit: 200 })
    const data = markRaw({
      nodes: res.nodes || [],
      links: res.links || [],
    })
    nodeCount.value = data.nodes.length
    linkCount.value = data.links.length
    legend.value = res.legend || {}
    if (renderer) renderer.stop()
    if (canvasRef.value) {
      renderer = useGraphRenderer(canvasRef, graphWidth, graphHeight)
      renderer.init(data, layoutMode.value)
    }
  } catch {}
}

function changeLayout(val) {
  if (!renderer) return
  const methods = {
    force: () => refreshData(),
    circle: () => renderer.applyCircleLayout(),
    tree: () => renderer.applyTreeLayout(),
    grid: () => renderer.applyGridLayout(),
  }
  methods[val]?.()
}

function zoomIn() { /* D3 zoom in handled by wheel */ }
function zoomOut() { /* D3 zoom out handled by wheel */ }
function resetView() { refreshData() }

function onCanvasClick(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  // Simple hit test - to be enhanced
  drawerVisible.value = false
}

onMounted(() => {
  graphWidth.value = window.innerWidth - 280
  graphHeight.value = window.innerHeight - 160
  refreshData()
})

onUnmounted(() => {
  if (renderer) renderer.stop()
})
</script>

<style scoped lang="scss">
.graph-workspace {
  height: calc(100vh - var(--topbar-height) - var(--spacing-lg) * 2);
  display: flex;
  flex-direction: column;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  .toolbar-actions { display: flex; gap: var(--spacing-sm); }
}

.graph-main {
  flex: 1;
  position: relative;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.graph-canvas {
  width: 100%;
  height: 100%;
  cursor: grab;
  &:active { cursor: grabbing; }
}

.legend-panel, .stats-panel {
  position: absolute;
  padding: var(--spacing-md);
  min-width: 140px;
  h4 { font-size: 13px; margin-bottom: var(--spacing-sm); }
}

.legend-panel { top: var(--spacing-md); right: var(--spacing-md); }
.stats-panel { top: var(--spacing-md); right: 200px; }

.legend-item {
  display: flex; align-items: center; gap: var(--spacing-sm);
  margin-bottom: 4px; font-size: 12px;
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
}

.stat-row {
  display: flex; justify-content: space-between; font-size: 13px;
  margin-bottom: 4px; gap: var(--spacing-md);
}
</style>
