<template>
  <div class="graph">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="2" y1="12" x2="22" y2="12"></line>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
        </svg>
        图谱可视化
      </h1>
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="搜索实体..."
          class="search-input"
          @keyup.enter="searchEntity"
        >
        <button class="search-btn" @click="searchEntity">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>
      </div>
    </div>

    <!-- 图谱区域 -->
    <div class="graph-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <div class="card">
          <h3>控制面板</h3>
          
          <!-- 实体筛选 -->
          <div class="control-section">
            <label>实体类型</label>
            <el-select v-model="selectedEntityType" multiple placeholder="选择实体类型" @change="applyFilters">
              <el-option 
                v-for="type in entityTypes" 
                :key="type.value" 
                :label="type.label" 
                :value="type.value"
              />
            </el-select>
          </div>

          <!-- 关系筛选 -->
          <div class="control-section">
            <label>关系类型</label>
            <el-select v-model="selectedRelationshipType" multiple placeholder="选择关系类型" @change="applyFilters">
              <el-option 
                v-for="type in relationshipTypes" 
                :key="type.value" 
                :label="type.label" 
                :value="type.value"
              />
            </el-select>
          </div>

          <!-- 布局选择 -->
          <div class="control-section">
            <label>布局方式</label>
            <el-select v-model="layoutType" @change="changeLayout">
              <el-option label="力导向布局" value="force" />
              <el-option label="环形布局" value="circular" />
              <el-option label="树形布局" value="tree" />
              <el-option label="网格布局" value="grid" />
            </el-select>
          </div>

          <!-- 节点大小 -->
          <div class="control-section">
            <label>节点大小</label>
            <el-slider 
              v-model="nodeSize" 
              :min="10" 
              :max="40" 
              :step="1"
              @change="updateNodeSize"
            />
          </div>

          <!-- 操作按钮 -->
          <div class="control-buttons">
            <button class="btn-primary" @click="refreshGraph">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
              </svg>
              刷新图谱
            </button>
            <button class="btn-secondary" @click="zoomIn">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                <line x1="11" y1="8" x2="11" y2="14"></line>
                <line x1="8" y1="11" x2="14" y2="11"></line>
              </svg>
              放大
            </button>
            <button class="btn-secondary" @click="zoomOut">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                <line x1="8" y1="11" x2="14" y2="11"></line>
              </svg>
              缩小
            </button>
            <button class="btn-secondary" @click="resetView">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                <path d="M3 3v5h5"></path>
                <path d="M21 12a9 9 0 1 0-9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
                <path d="M16 16h5v5"></path>
              </svg>
              重置视图
            </button>
            <button class="btn-secondary" @click="exportGraph">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              导出图谱
            </button>
          </div>
        </div>
      </div>

      <!-- 中间图谱可视化区域 -->
      <div class="graph-main">
        <div class="graph-canvas" ref="graphCanvas">
          <!-- 加载状态 -->
          <div v-if="loading" class="loading-overlay">
            <div class="loading-spinner"></div>
            <div class="loading-text">加载图谱数据中...</div>
          </div>
          <!-- 加载错误提示 -->
          <div v-else-if="loadError" class="error-overlay">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="error-icon">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <div class="error-text">图谱数据加载失败</div>
            <div class="error-subtext">正在使用默认数据</div>
          </div>
        </div>
        <div class="graph-info" v-if="selectedNode">
          <div class="info-header">
            <h4>实体详情</h4>
            <button class="close-btn" @click="selectedNode = null">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="node-details">
            <div class="detail-item">
              <span class="label">名称：</span>
              <span class="value">{{ selectedNode.name }}</span>
            </div>
            <div class="detail-item">
              <span class="label">类型：</span>
              <span class="value" :style="{ color: getNodeColor(selectedNode.type) }">{{ selectedNode.type }}</span>
            </div>
            <div class="detail-item">
              <span class="label">描述：</span>
              <span class="value">{{ selectedNode.description || '无' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">相关实体：</span>
              <div class="related-entities">
                <span 
                  v-for="(related, index) in selectedNode.related" 
                  :key="index" 
                  class="related-tag"
                  @click="selectNode(related.id)"
                >
                  {{ related.name }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧信息面板 -->
      <div class="right-panel">
        <!-- 图例 -->
        <div class="card">
          <h3>图例</h3>
          <div class="legend">
            <div class="legend-item">
              <div class="legend-color entity"></div>
              <span>实体</span>
            </div>
            <div class="legend-item">
              <div class="legend-color relationship"></div>
              <span>关系</span>
            </div>
            <div v-for="type in entityTypes" :key="type.value" class="legend-item">
              <div class="legend-color" :style="{ backgroundColor: getNodeColor(type.value) }"></div>
              <span>{{ type.label }}</span>
            </div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="card">
          <h3>统计信息</h3>
          <div class="stats">
            <div class="stat-item">
              <div class="stat-value">{{ graphStats.nodes }}</div>
              <div class="stat-label">实体数量</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ graphStats.edges }}</div>
              <div class="stat-label">关系数量</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ graphStats.types }}</div>
              <div class="stat-label">实体类型</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ graphStats.density.toFixed(2) }}</div>
              <div class="stat-label">图谱密度</div>
            </div>
          </div>
        </div>

        <!-- 操作提示 -->
        <div class="card">
          <h3>操作提示</h3>
          <div class="tips">
            <div class="tip-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>点击节点查看详情</span>
            </div>
            <div class="tip-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>拖拽节点调整位置</span>
            </div>
            <div class="tip-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>滚轮缩放视图</span>
            </div>
            <div class="tip-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>点击图例筛选实体</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'

// 图谱容器
const graphCanvas = ref(null)

// 加载状态
const loading = ref(false)
const loadError = ref(false)

// 图谱数据
const graphData = ref({
  nodes: [
    { id: 1, name: '知识图谱', type: 'concept', description: '一种结构化的知识表示方法' },
    { id: 2, name: '实体', type: 'concept', description: '知识图谱中的基本元素' },
    { id: 3, name: '关系', type: 'concept', description: '实体之间的连接' },
    { id: 4, name: '智能问答', type: 'application', description: '基于知识图谱的问答系统' },
    { id: 5, name: '推荐系统', type: 'application', description: '利用知识图谱提升推荐质量' },
    { id: 6, name: 'GraphRAG', type: 'tool', description: '基于图的检索增强生成' },
    { id: 7, name: 'FastAPI', type: 'technology', description: 'Web框架' },
    { id: 8, name: 'SQLite', type: 'database', description: '轻量级数据库' },
    { id: 9, name: '智谱AI', type: 'technology', description: '大语言模型' }
  ],
  links: [
    { source: 1, target: 2, type: 'has_part', label: '包含' },
    { source: 1, target: 3, type: 'has_part', label: '包含' },
    { source: 1, target: 4, type: 'used_in', label: '应用于' },
    { source: 1, target: 5, type: 'used_in', label: '应用于' },
    { source: 6, target: 1, type: 'uses', label: '使用' },
    { source: 7, target: 1, type: 'powers', label: '驱动' },
    { source: 8, target: 1, type: 'stores', label: '存储' },
    { source: 9, target: 6, type: 'powers', label: '驱动' }
  ]
})

// 选择状态
const selectedEntityType = ref([])
const selectedRelationshipType = ref([])
const layoutType = ref('force')
const selectedNode = ref(null)
const searchQuery = ref('')
const nodeSize = ref(20)

// 实体类型
const entityTypes = ref([
  { label: '概念', value: 'concept' },
  { label: '应用', value: 'application' },
  { label: '工具', value: 'tool' },
  { label: '数据库', value: 'database' },
  { label: '技术', value: 'technology' }
])

// 关系类型
const relationshipTypes = ref([
  { label: '包含', value: 'has_part' },
  { label: '应用于', value: 'used_in' },
  { label: '使用', value: 'uses' },
  { label: '存储', value: 'stores' },
  { label: '驱动', value: 'powers' }
])

// 图谱统计
const graphStats = ref({
  nodes: 9,
  edges: 8,
  types: 5,
  density: 0.25
})

// D3实例
let simulation = null
let svg = null
let zoom = null
let container = null

// 加载图谱数据
const loadGraphData = async () => {
  loading.value = true
  loadError.value = false
  
  try {
    // 尝试从后端API加载数据
    const response = await fetch('http://localhost:8013/api/graph/data')
    if (response.ok) {
      const data = await response.json()
      if (data.nodes && data.links) {
        graphData.value = data
        updateGraphStats()
      }
    } else {
      // 加载失败，使用默认数据
      console.warn('Failed to load graph data, using default data')
      loadError.value = true
    }
  } catch (error) {
    // 网络错误，使用默认数据
    console.error('Error loading graph data:', error)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

// 更新图谱统计
const updateGraphStats = () => {
  const nodes = graphData.value.nodes.length
  const edges = graphData.value.links.length
  const types = new Set(graphData.value.nodes.map(node => node.type)).size
  const density = edges / (nodes * (nodes - 1)) || 0
  
  graphStats.value = {
    nodes,
    edges,
    types,
    density
  }
}

// 初始化图谱
const initGraph = () => {
  if (!graphCanvas.value) return

  // 清空容器
  d3.select(graphCanvas.value).selectAll('*').remove()

  const width = graphCanvas.value.clientWidth
  const height = graphCanvas.value.clientHeight

  // 创建SVG和容器
  svg = d3.select(graphCanvas.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)

  // 添加缩放功能
  zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      container.attr('transform', event.transform)
    })

  svg.call(zoom)

  // 创建容器
  container = svg.append('g')

  // 应用布局
  applyLayout()

  // 重置视图，确保图谱居中
  setTimeout(() => {
    if (svg) {
      svg.transition().call(zoom.transform, d3.zoomIdentity)
    }
  }, 500)
}

// 应用布局
const applyLayout = () => {
  if (!graphCanvas.value) return

  const width = graphCanvas.value.clientWidth
  const height = graphCanvas.value.clientHeight

  // 清空容器
  container.selectAll('*').remove()

  // 根据布局类型创建不同的模拟
  switch (layoutType.value) {
    case 'force':
      simulation = d3.forceSimulation(graphData.value.nodes)
        .force('link', d3.forceLink(graphData.value.links).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-350))
        .force('center', d3.forceCenter(width / 2, height / 2))
      break
    case 'circular':
      // 环形布局
      const radius = Math.min(width, height) / 3
      graphData.value.nodes.forEach((node, i) => {
        const angle = (i / graphData.value.nodes.length) * 2 * Math.PI
        node.x = width / 2 + radius * Math.cos(angle)
        node.y = height / 2 + radius * Math.sin(angle)
      })
      simulation = null
      break
    case 'tree':
      // 简单树形布局
      const treeLayout = d3.tree().size([height - 100, width - 100])
      const root = d3.hierarchy({ children: graphData.value.nodes })
      const treeData = treeLayout(root)
      graphData.value.nodes.forEach((node, i) => {
        node.x = treeData.children[i].x + 50
        node.y = treeData.children[i].y + 50
      })
      simulation = null
      break
    case 'grid':
      // 网格布局
      const gridSize = Math.ceil(Math.sqrt(graphData.value.nodes.length))
      const cellSize = Math.min(width, height) / (gridSize + 1)
      graphData.value.nodes.forEach((node, i) => {
        node.x = (i % gridSize + 0.5) * cellSize + 50
        node.y = (Math.floor(i / gridSize) + 0.5) * cellSize + 50
      })
      simulation = null
      break
  }

  // 绘制连接线
  const link = container.append('g')
    .selectAll('line')
    .data(graphData.value.links)
    .enter()
    .append('line')
    .attr('class', 'link')
    .attr('stroke', '#999')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', 2)

  // 绘制节点
  const node = container.append('g')
    .selectAll('circle')
    .data(graphData.value.nodes)
    .enter()
    .append('circle')
    .attr('class', 'node')
    .attr('r', nodeSize.value)
    .attr('fill', d => getNodeColor(d.type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('click', (event, d) => selectNode(d.id))
    .on('mouseover', (event, d) => {
      d3.select(event.currentTarget)
        .transition()
        .duration(200)
        .attr('r', nodeSize.value + 5)
        .attr('stroke-width', 3)
    })
    .on('mouseout', (event, d) => {
      d3.select(event.currentTarget)
        .transition()
        .duration(200)
        .attr('r', nodeSize.value)
        .attr('stroke-width', 2)
    })

  // 添加节点标签
  const label = container.append('g')
    .selectAll('text')
    .data(graphData.value.nodes)
    .enter()
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', 5)
    .text(d => d.name)
    .attr('fill', '#333')
    .attr('font-size', '12px')
    .attr('font-weight', '500')

  // 添加关系标签
  const linkLabel = container.append('g')
    .selectAll('text')
    .data(graphData.value.links)
    .enter()
    .append('text')
    .attr('text-anchor', 'middle')
    .text(d => d.label)
    .attr('fill', '#666')
    .attr('font-size', '10px')
    .attr('font-weight', '400')

  // 模拟更新
  if (simulation) {
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y + nodeSize.value + 15)

      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2)
    })
  } else {
    // 非力导向布局，直接设置位置
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    label
      .attr('x', d => d.x)
      .attr('y', d => d.y + nodeSize.value + 15)

    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2)
  }
}

// 拖拽函数
const dragstarted = (event, d) => {
  if (simulation && !event.active) simulation.alphaTarget(0.3).restart()
  d.fx = d.x
  d.fy = d.y
}

const dragged = (event, d) => {
  d.fx = event.x
  d.fy = event.y
}

const dragended = (event, d) => {
  if (simulation && !event.active) simulation.alphaTarget(0)
  d.fx = null
  d.fy = null
}

// 获取节点颜色
const getNodeColor = (type) => {
  const colors = {
    concept: '#667eea',
    application: '#764ba2',
    tool: '#f093fb',
    database: '#4facfe',
    technology: '#43e97b'
  }
  return colors[type] || '#999'
}

// 选择节点
const selectNode = (nodeId) => {
  const node = graphData.value.nodes.find(n => n.id === nodeId)
  if (node) {
    // 查找相关实体
    const related = []
    graphData.value.links.forEach(link => {
      if (link.source.id === nodeId) {
        const targetNode = graphData.value.nodes.find(n => n.id === link.target.id)
        if (targetNode) {
          related.push({ id: targetNode.id, name: targetNode.name })
        }
      }
      if (link.target.id === nodeId) {
        const sourceNode = graphData.value.nodes.find(n => n.id === link.source.id)
        if (sourceNode) {
          related.push({ id: sourceNode.id, name: sourceNode.name })
        }
      }
    })
    selectedNode.value = { ...node, related }
  }
}

// 刷新图谱
const refreshGraph = () => {
  loadGraphData().then(() => {
    initGraph()
  })
}

// 放大
const zoomIn = () => {
  if (svg) {
    svg.transition().call(zoom.scaleBy, 1.3)
  }
}

// 缩小
const zoomOut = () => {
  if (svg) {
    svg.transition().call(zoom.scaleBy, 0.7)
  }
}

// 重置视图
const resetView = () => {
  if (svg) {
    svg.transition().call(zoom.transform, d3.zoomIdentity)
  }
  initGraph()
}

// 导出图谱
const exportGraph = () => {
  if (!svg) return
  
  // 创建SVG字符串
  const svgString = new XMLSerializer().serializeToString(svg.node())
  const blob = new Blob([svgString], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  
  // 创建下载链接
  const link = document.createElement('a')
  link.href = url
  link.download = 'knowledge-graph.svg'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// 搜索实体
const searchEntity = () => {
  if (!searchQuery.value) return
  
  const node = graphData.value.nodes.find(n => 
    n.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
  
  if (node) {
    selectNode(node.id)
    // 可以添加定位到节点的逻辑
  }
}

// 应用筛选
const applyFilters = () => {
  // 这里可以实现筛选逻辑
  console.log('应用筛选', selectedEntityType.value, selectedRelationshipType.value)
  // 实际应用中，这里应该根据筛选条件过滤节点和边
  initGraph()
}

// 更改布局
const changeLayout = () => {
  applyLayout()
}

// 更新节点大小
const updateNodeSize = () => {
  if (container) {
    container.selectAll('.node')
      .transition()
      .duration(300)
      .attr('r', nodeSize.value)
    
    container.selectAll('text')
      .transition()
      .duration(300)
      .attr('y', d => d.y + nodeSize.value + 15)
  }
}

onMounted(() => {
  loadGraphData().then(() => {
    initGraph()
  })
  window.addEventListener('resize', initGraph)
})

onUnmounted(() => {
  window.removeEventListener('resize', initGraph)
  if (simulation) {
    simulation.stop()
  }
})
</script>

<style scoped>
.graph {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .search-box {
      display: flex;
      align-items: center;
      background: #f5f7fa;
      border-radius: 8px;
      padding: 4px 12px;
      transition: all 0.3s ease;
      
      &:hover {
        background: #ecf5ff;
      }
      
      .search-input {
        border: none;
        background: transparent;
        padding: 8px;
        font-size: 14px;
        color: #303133;
        outline: none;
        width: 200px;
        
        &::placeholder {
          color: #909399;
        }
      }
      
      .search-btn {
        background: none;
        border: none;
        color: #606266;
        cursor: pointer;
        padding: 4px;
        transition: all 0.3s ease;
        
        &:hover {
          color: #409eff;
        }
      }
    }
  }

  .graph-container {
    display: grid;
    grid-template-columns: 280px 1fr 280px;
    gap: 20px;
    height: calc(100vh - 180px);
    max-height: 800px;

    @media (max-width: 1200px) {
      grid-template-columns: 260px 1fr 260px;
    }

    @media (max-width: 992px) {
      grid-template-columns: 1fr;
      height: auto;
      max-height: none;
    }
  }

  .left-panel,
  .right-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;

    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      padding: 20px;
      transition: all 0.3s ease;
      
      &:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
      }

      h3 {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 16px;
        color: #303133;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .control-section {
        margin-bottom: 20px;
        label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #606266;
          margin-bottom: 10px;
        }
      }

      .control-buttons {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 16px;
      }

      .legend {
        .legend-item {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
          font-size: 13px;
          color: #606266;
          cursor: pointer;
          padding: 4px 8px;
          border-radius: 4px;
          transition: all 0.3s ease;
          
          &:hover {
            color: #303133;
            background: #f5f7fa;
          }

          .legend-color {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 2px solid #fff;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            &.entity { background: #667eea; }
            &.relationship { background: #999; }
          }
        }
      }

      .stats {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;

        .stat-item {
          text-align: center;
          background: #f5f7fa;
          padding: 12px;
          border-radius: 8px;
          transition: all 0.3s ease;
          
          &:hover {
            background: #ecf5ff;
            transform: translateY(-2px);
          }
          
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

      .tips {
        .tip-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          margin-bottom: 12px;
          font-size: 13px;
          color: #606266;
          
          svg {
            flex-shrink: 0;
            margin-top: 2px;
            color: #409eff;
          }
        }
      }
    }
  }

  .graph-main {
    position: relative;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .graph-canvas {
      width: 100%;
      height: 100%;
      position: relative;
      flex: 1;

      .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 100;

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #667eea;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 16px;
        }

        .loading-text {
          font-size: 14px;
          color: #606266;
        }
      }

      .error-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 100;

        .error-icon {
          color: #f56c6c;
          margin-bottom: 16px;
        }

        .error-text {
          font-size: 16px;
          font-weight: 500;
          color: #f56c6c;
          margin-bottom: 8px;
        }

        .error-subtext {
          font-size: 14px;
          color: #909399;
        }
      }
    }

    .graph-info {
      position: absolute;
      top: 24px;
      right: 24px;
      width: 320px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
      padding: 20px;
      z-index: 10;
      transition: all 0.3s ease;
      animation: slideIn 0.3s ease-out;

      .info-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        
        h4 {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin: 0;
        }
        
        .close-btn {
          background: none;
          border: none;
          color: #909399;
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
          transition: all 0.3s ease;
          
          &:hover {
            background: #f5f7fa;
            color: #606266;
          }
        }
      }

      .node-details {
        .detail-item {
          margin-bottom: 12px;
          font-size: 14px;

          .label {
            font-weight: 500;
            color: #606266;
            margin-right: 10px;
          }
          .value {
            color: #303133;
            word-break: break-word;
          }
        }

        .related-entities {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 8px;

          .related-tag {
            background: #f0f9ff;
            color: #409eff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              background: #ecf5ff;
              transform: translateY(-1px);
              box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
            }
          }
        }
      }
    }
  }
}

/* D3样式 */
.link {
  stroke: #999;
  stroke-opacity: 0.6;
  stroke-width: 2px;
  transition: all 0.3s ease;
  
  &:hover {
    stroke: #667eea;
    stroke-opacity: 1;
    stroke-width: 3px;
  }
}

.node {
  stroke: #fff;
  stroke-width: 2px;
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    stroke-width: 3px;
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

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
