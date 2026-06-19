// ============================================================
// Canvas 图谱渲染器 — D3 力导向布局 + Canvas 2D
// v2.2: 自适应布局 / 虚线弱关联 / 类型筛选 / centerOn
// ============================================================
import * as d3 from 'd3'

export function useGraphRenderer(canvasRef, width, height, onNodeClick) {
  let ctx = null
  let canvas = null
  let simulation = null
  let nodes = []
  let links = []
  let allNodes = []        // 完整节点集（含隐藏的）
  let allLinks = []        // 完整边集
  let transform = d3.zoomIdentity
  let hoveredNode = null
  let selectedNode = null
  let sizeScale = 1.0
  let hiddenTypes = new Set()
  let minWeight = 0.0

  // ─── 布局参数 ──────────────────────────────────────────────

  function adaptiveCharge(nodeCount) {
    // 节点越多，斥力越强以保持间距
    if (nodeCount < 15) return -300
    if (nodeCount < 30) return -400
    if (nodeCount < 60) return -550
    return -700
  }

  function linkDistance(link) {
    // 弱关联/虚线边用更长的距离
    if (link.dashed || link.relation === '弱关联') return 180
    // 强关联按权重：高权重更近
    const v = link.value || 0.5
    return 60 + (1 - v) * 100
  }

  function nodeRadius(n) {
    const base = Math.max(5, Math.min(26, (n.weight || 0.5) * 27))
    return base * sizeScale
  }

  function maxNodeRadius() {
    return 26 * sizeScale
  }

  // ─── 初始化 ────────────────────────────────────────────────

  function init(data, scale = 1.0) {
    if (!canvasRef.value) return
    sizeScale = scale
    canvas = canvasRef.value
    const dpr = window.devicePixelRatio || 1
    canvas.width = width.value * dpr
    canvas.height = height.value * dpr
    canvas.style.width = width.value + 'px'
    canvas.style.height = height.value + 'px'
    ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    // Zoom
    d3.select(canvas).call(
      d3.zoom()
        .scaleExtent([0.2, 5])
        .on('zoom', (e) => { transform = e.transform; draw() })
    )

    // Click
    d3.select(canvas).on('click', (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left - transform.x) / transform.k
      const my = (e.clientY - rect.top - transform.y) / transform.k
      const hit = hitTest(mx, my)
      if (onNodeClick) onNodeClick(hit)
      selectedNode = hit
      draw()
    })

    // Hover
    d3.select(canvas).on('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left - transform.x) / transform.k
      const my = (e.clientY - rect.top - transform.y) / transform.k
      const prev = hoveredNode
      hoveredNode = hitTest(mx, my)
      if (prev !== hoveredNode) {
        canvas.style.cursor = hoveredNode ? 'pointer' : 'grab'
        draw()
      }
    })

    // 存储完整数据
    allNodes = data.nodes.map((n, i) => ({
      ...n,
      x: width.value / 2 + (Math.random() - 0.5) * 200,
      y: height.value / 2 + (Math.random() - 0.5) * 200,
      index: i,
    }))

    allLinks = data.links.map(l => ({
      ...l,
      source: allNodes.find(n => n.id === l.source) || l.source,
      target: allNodes.find(n => n.id === l.target) || l.target,
    }))

    applyFilters()
    startSimulation()
  }

  function applyFilters() {
    // 按类型和权重过滤可见节点
    const visibleNodes = allNodes.filter(n => {
      if (hiddenTypes.has(n.type)) return false
      if ((n.weight || 0) < minWeight) return false
      return true
    })
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id))

    nodes = visibleNodes
    links = allLinks.filter(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source
      const tid = typeof l.target === 'object' ? l.target.id : l.target
      return visibleNodeIds.has(sid) && visibleNodeIds.has(tid)
    })
  }

  function startSimulation() {
    if (simulation) simulation.stop()

    const collideR = Math.max(10, maxNodeRadius() * 1.5)

    simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(l => linkDistance(l)))
      .force('charge', d3.forceManyBody().strength(adaptiveCharge(nodes.length)))
      .force('center', d3.forceCenter(width.value / 2, height.value / 2))
      .force('collision', d3.forceCollide(collideR))
      .on('tick', draw)

    // 按类型分组力 (可选)
    const types = [...new Set(nodes.map(n => n.type))]
    if (types.length >= 2 && types.length <= 6) {
      const radius = Math.min(width.value, height.value) * 0.35
      types.forEach((t, i) => {
        const angle = (2 * Math.PI * i) / types.length
        const cx = width.value / 2 + radius * Math.cos(angle)
        const cy = height.value / 2 + radius * Math.sin(angle)
        simulation.force(`x_${t}`, d3.forceX(cx).strength(0.03))
        simulation.force(`y_${t}`, d3.forceY(cy).strength(0.03))
      })
    }
  }

  // ─── 公共控制方法 ───────────────────────────────────────────

  function setNodeSizeScale(s) {
    sizeScale = s
    if (simulation) {
      // 更新碰撞半径
      const collideR = Math.max(10, maxNodeRadius() * 1.5)
      simulation.force('collision', d3.forceCollide(collideR))
      simulation.alpha(0.3).restart()
    }
  }

  function setHiddenTypes(types) {
    hiddenTypes = new Set(types)
    applyFilters()
    startSimulation()
  }

  function setMinWeight(w) {
    minWeight = w
    applyFilters()
    startSimulation()
  }

  function centerOn(node) {
    if (!node || !canvas) return
    selectedNode = node

    const targetX = node.x
    const targetY = node.y
    const tx = width.value / 2 - targetX * transform.k
    const ty = height.value / 2 - targetY * transform.k

    d3.select(canvas)
      .transition()
      .duration(500)
      .call(
        d3.zoom().transform,
        d3.zoomIdentity.translate(tx, ty).scale(Math.max(0.5, transform.k))
      )

    draw()
  }

  // ─── 碰撞检测 ──────────────────────────────────────────────

  function hitTest(mx, my) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]
      const r = nodeRadius(n)
      const dx = mx - n.x
      const dy = my - n.y
      if (dx * dx + dy * dy <= (r + 4) * (r + 4)) return n
    }
    return null
  }

  // ─── 绘制 ──────────────────────────────────────────────────

  function draw() {
    if (!ctx || !canvas) return
    const w = width.value
    const h = height.value
    ctx.save()
    ctx.clearRect(0, 0, w, h)
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.k, transform.k)

    // ---- 边 (按虚线/实线分组渲染) ----
    for (const l of links) {
      const sx = l.source?.x
      const sy = l.source?.y
      const tx = l.target?.x
      const ty = l.target?.y
      if (sx == null || tx == null) continue

      const hl = hoveredNode && (l.source === hoveredNode || l.target === hoveredNode)
      const sl = selectedNode && (l.source === selectedNode || l.target === selectedNode)
      const isDashed = l.dashed || l.relation === '弱关联'

      ctx.beginPath()
      ctx.moveTo(sx, sy)
      ctx.lineTo(tx, ty)

      if (isDashed) {
        // 虚线弱关联边
        ctx.setLineDash([4, 6])
        ctx.strokeStyle = sl ? '#4F8CF7' : hl ? '#B0BEC5' : '#D0D8E8'
        ctx.lineWidth = sl ? 1.5 : 0.8
        ctx.globalAlpha = sl ? 0.9 : (hl ? 0.6 : 0.35)
      } else {
        ctx.setLineDash([])
        ctx.strokeStyle = sl ? '#4F8CF7' : hl ? '#7CABFF' : '#C0C8D8'
        ctx.lineWidth = (hl || sl) ? 2.0 : Math.max(0.6, (l.value || 0.5) * 1.4)
        ctx.globalAlpha = 1.0
      }

      ctx.stroke()

      // 关系标签（缩放 > 0.45 或高亮时显示；弱关联在更高缩放时才显示）
      const labelThreshold = isDashed ? 0.65 : 0.45
      if (transform.k > labelThreshold && (hl || sl || transform.k > (isDashed ? 0.85 : 0.7))) {
        const mx = (sx + tx) / 2
        const my = (sy + ty) / 2
        ctx.fillStyle = isDashed ? '#B0BEC5' : (hl ? '#4F8CF7' : '#8B95A8')
        ctx.globalAlpha = isDashed ? 0.6 : 1.0
        const fs = Math.max(10, 11 / transform.k)
        ctx.font = `${fs}px -apple-system, "PingFang SC", sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        const label = l.relation || ''
        if (label) ctx.fillText(label, mx, my - 4)
      }

      ctx.setLineDash([])
      ctx.globalAlpha = 1.0
    }

    // ---- 节点 ----
    for (const n of nodes) {
      const r = nodeRadius(n)
      const isHovered = n === hoveredNode
      const isSelected = n === selectedNode

      // 发光晕（选中/悬停时）
      if (isHovered || isSelected) {
        ctx.beginPath()
        ctx.arc(n.x, n.y, r + 8, 0, Math.PI * 2)
        ctx.fillStyle = isSelected ? 'rgba(79,140,247,0.25)' : 'rgba(79,140,247,0.12)'
        ctx.fill()
      }

      // 圆形节点
      ctx.beginPath()
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
      ctx.fillStyle = n.color || '#4F8CF7'
      ctx.fill()

      // 边框
      ctx.strokeStyle = isSelected ? '#4F8CF7' : isHovered ? '#7CABFF' : 'rgba(255,255,255,0.7)'
      ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.2
      ctx.stroke()

      // 标签
      if (isHovered || isSelected || transform.k > 0.45) {
        const fs = isHovered || isSelected ? 13 : Math.max(10, 11 / transform.k)
        ctx.fillStyle = '#1A1A2E'
        ctx.font = `600 ${fs}px -apple-system, "PingFang SC", sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(n.name, n.x, n.y + r + 6)
      }
    }

    ctx.restore()
  }

  function stop() {
    if (simulation) simulation.stop()
  }

  function resize(w, h) {
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
    if (ctx) { ctx.scale(dpr, dpr); draw() }
  }

  return {
    init, stop, resize, draw,
    setNodeSizeScale, setHiddenTypes, setMinWeight, centerOn,
  }
}
