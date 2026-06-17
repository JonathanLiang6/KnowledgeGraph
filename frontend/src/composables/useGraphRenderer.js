// ============================================================
// Canvas 图谱渲染器 - D3.js force simulation + Canvas 2D
// 使用 markRaw/shallowRef 避免 Vue 深度响应式
// ============================================================
import * as d3 from 'd3'

export function useGraphRenderer(canvasRef, width, height) {
  let ctx = null
  let simulation = null
  let nodes = []
  let links = []
  let transform = d3.zoomIdentity

  const GRID_LAYOUT = 'grid'
  const CIRCLE_LAYOUT = 'circle'
  const TREE_LAYOUT = 'tree'

  function init(data, layout = 'force') {
    if (!canvasRef.value) return
    const canvas = canvasRef.value
    canvas.width = width.value
    canvas.height = height.value
    ctx = canvas.getContext('2d')
    d3.select(canvas).call(
      d3.zoom().scaleExtent([0.1, 4]).on('zoom', (e) => { transform = e.transform; draw() })
    )

    nodes = data.nodes.map(n => ({ ...n }))
    links = data.links.map(l => ({ ...l }))

    // Force simulation
    simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(canvas.width / 2, canvas.height / 2))
      .force('collision', d3.forceCollide(20))
      .on('tick', draw)

    if (layout === CIRCLE_LAYOUT) applyCircleLayout()
    if (layout === TREE_LAYOUT) applyTreeLayout()
    if (layout === GRID_LAYOUT) applyGridLayout()
  }

  function applyCircleLayout() {
    const cx = width.value / 2
    const cy = height.value / 2
    const r = Math.min(cx, cy) * 0.7
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length
      n.x = cx + r * Math.cos(angle)
      n.y = cy + r * Math.sin(angle)
    })
    simulation.alpha(0.1).restart()
  }

  function applyTreeLayout() {
    const root = d3.stratify()(nodes.filter(n => links.some(l => l.source.id === n.id || l.source === n.id)))
    const treeLayout = d3.tree().size([width.value - 100, height.value - 100])
    treeLayout(root)
    root.descendants().forEach((d, i) => {
      if (nodes[i]) { nodes[i].x = d.x + 50; nodes[i].y = d.y + 50 }
    })
    simulation.alpha(0.1).restart()
  }

  function applyGridLayout() {
    const cols = Math.ceil(Math.sqrt(nodes.length))
    const spacing = Math.min(width.value / cols, 120)
    nodes.forEach((n, i) => {
      n.x = (i % cols) * spacing + spacing / 2
      n.y = Math.floor(i / cols) * spacing + spacing / 2
    })
    simulation.alpha(0.1).restart()
  }

  function draw() {
    if (!ctx || !canvasRef.value) return
    ctx.save()
    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.k, transform.k)

    // Draw links
    links.forEach(l => {
      ctx.beginPath()
      ctx.moveTo(l.source.x, l.source.y)
      ctx.lineTo(l.target.x, l.target.y)
      ctx.strokeStyle = '#D0D5E0'
      ctx.lineWidth = Math.max(0.5, (l.value || 1) * 0.5)
      ctx.stroke()
    })

    // Draw nodes
    nodes.forEach(n => {
      ctx.beginPath()
      const r = Math.max(4, (n.weight || 1) * 10)
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
      ctx.fillStyle = n.color || '#4F8CF7'
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Label
      if (transform.k > 0.5) {
        ctx.fillStyle = '#1A1A2E'
        ctx.font = `${Math.min(12, 10 / transform.k)}px sans-serif`
        ctx.textAlign = 'center'
        ctx.fillText(n.name, n.x, n.y + r + 12)
      }
    })

    ctx.restore()
  }

  function stop() {
    if (simulation) simulation.stop()
  }

  return { init, applyCircleLayout, applyTreeLayout, applyGridLayout, stop }
}
