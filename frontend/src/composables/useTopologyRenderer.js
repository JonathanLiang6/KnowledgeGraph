/**
 * useTopologyRenderer.js - v4.2 拓扑导航 D3 三层轨道布局渲染
 *
 * 纯 Canvas 渲染，事件通过回调外传给 Vue 组件处理。
 * 三层结构：根节点(中心) → 分支节点(轨道1) → KB节点(轨道2)
 *
 * 布局策略：
 *   1. 入场动画：逐级从中心展开到目标轨道位置（1.5s）
 *   2. 柔和力微调：入场完成后，持续运行手写力循环
 *      - 碰撞检测：同级节点重叠时互相推开
 *      - 轨道回弹：偏离轨道的节点被拉回
 *      - 呼吸漂移：节点在目标位置附近轻微浮动，保持"活"的感觉
 *      - 不使用 d3.forceSimulation，避免力系互相干扰破坏布局
 */
import * as d3 from 'd3'

export function useTopologyRenderer(hostRef, opts = {}) {
  const { onNodeClick, onNodeDblClick, onNodeRightClick, onCanvasClick, onCanvasRightClick } = opts

  let canvas, ctx, transform = d3.zoomIdentity
  let nodes = [], links = []
  let rafId = null
  let clickTimer = null
  let selectedNodeId = null

  // 轨道半径配置
  const ORBIT_BRANCH = 240   // 分支节点轨道半径
  const ORBIT_KB = 400       // KB 节点轨道半径

  // 力参数 — 非常温和，只做微调
  const COLLIDE_DIST = 90    // 触发碰撞推开的最小距离
  const PUSH_FORCE = 0.08    // 碰撞推开的力度
  const PULL_FORCE = 0.04    // 拉回轨道的力度
  const SHRINK_DIST = 24     // 收缩距离（KB节点向中心收缩）
  const SHRINK_DURATION = 600 // 收缩时长 ms

  // 入场动画
  let enterStart = 0
  let enterAnimating = false
  let forceLoopRunning = false
  let shrinkAnimating = false
  let shrinkStart = 0
  const ENTER_TOTAL = 1500   // 入场总时长（加速到 1.5s）
  const ENTER_PHASES = [
    { tier: 0, delay: 0, duration: 300 },    // root
    { tier: 1, delay: 200, duration: 600 },  // branch
    { tier: 2, delay: 600, duration: 800 },  // KB
  ]

  function nodeTier(n) {
    if (n.is_root) return 0
    if (!n.kb_id) return 1
    return 2
  }

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3)
  }

  // v4.1: 轻微回弹缓动 — 展开到位时带一点弹性 overshoot，比纯 easeOut 更有生命感
  function easeOutBack(t) {
    const c1 = 1.15, c3 = c1 + 1
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
  }

  function getEnterProgress(n) {
    if (!enterAnimating) return 1
    const elapsed = performance.now() - enterStart
    const tier = nodeTier(n)
    const phase = ENTER_PHASES.find(p => p.tier === tier)
    if (!phase) return 1
    // v4.1: 同层节点按 id 错峰 0-125ms，避免整层"齐步走"的机械感
    const stagger = (n.id.charCodeAt(n.id.length - 1) % 5) * 25
    if (elapsed < phase.delay + stagger) return 0
    const localT = Math.min((elapsed - phase.delay - stagger) / phase.duration, 1)
    return Math.max(0, easeOutBack(localT))
  }

  function startEnterAnimation() {
    enterStart = performance.now()
    enterAnimating = true
    forceLoopRunning = false
    shrinkAnimating = false

    function animLoop() {
      if (!enterAnimating) return
      const elapsed = performance.now() - enterStart
      schedule()
      if (elapsed < ENTER_TOTAL) {
        requestAnimationFrame(animLoop)
      } else {
        enterAnimating = false
        startShrinkAnimation()
      }
    }
    requestAnimationFrame(animLoop)
  }

  /**
   * 收缩动画 — 入场结束后，KB节点略微向中心收缩
   */
  function startShrinkAnimation() {
    shrinkStart = performance.now()
    shrinkAnimating = true

    function animLoop() {
      if (!shrinkAnimating) return
      const elapsed = performance.now() - shrinkStart
      const progress = Math.min(elapsed / SHRINK_DURATION, 1)

      // KB节点向中心收缩
      const shrinkFactor = easeOutCubic(progress)
      nodes.forEach(n => {
        if (!n.kb_id || n.is_root || n.x == null || n.y == null) return
        const host = hostRef.value
        const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
        const cx = cw / 2, cy = ch / 2
        const dx = n.x - cx
        const dy = n.y - cy
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        // 向中心收缩 SHRINK_DIST
        const newDist = ORBIT_KB - SHRINK_DIST * shrinkFactor
        n.x = cx + (dx / dist) * newDist
        n.y = cy + (dy / dist) * newDist
      })

      schedule()
      if (elapsed < SHRINK_DURATION) {
        requestAnimationFrame(animLoop)
      } else {
        shrinkAnimating = false
        startGentleForceLoop()
      }
    }
    requestAnimationFrame(animLoop)
  }

  /**
   * 柔和力循环 — 入场完成后持续运行
   *
   * 不用 d3.forceSimulation，只做三件事：
   *   1. 碰撞推开：同级节点距离 < COLLIDE_DIST 时互相推开
   *   2. 轨道回弹：将节点拉回目标轨道半径（强约束）
   *   3. 角度稳定：将节点拉回目标角度（防止力推开打乱角度分布）
   *   4. 呼吸漂移：在目标位置附近轻微浮动，保持"活"的感觉
   */
  function startGentleForceLoop() {
    if (forceLoopRunning) return
    forceLoopRunning = true

    const host = hostRef.value
    const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
    const cx = cw / 2, cy = ch / 2

    function tick() {
      if (!forceLoopRunning) return

      const now = performance.now()

      // 按层分组
      const branches = nodes.filter(n => !n.is_root && !n.kb_id)
      const kbs = nodes.filter(n => n.kb_id)

      // ── 碰撞推开：同级节点 ──
      const pushApart = (group) => {
        for (let i = 0; i < group.length; i++) {
          for (let j = i + 1; j < group.length; j++) {
            const a = group[i], b = group[j]
            if (a.x == null || b.x == null) continue
            const dx = b.x - a.x
            const dy = b.y - a.y
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            if (dist < COLLIDE_DIST) {
              const force = (COLLIDE_DIST - dist) * PUSH_FORCE
              const fx = (dx / dist) * force
              const fy = (dy / dist) * force
              a.x -= fx; a.y -= fy
              b.x += fx; b.y += fy
            }
          }
        }
      }
      pushApart(branches)
      pushApart(kbs)

      // ── 轨道回弹 + 角度稳定 ──
      nodes.forEach(n => {
        if (n.is_root || n.x == null) return
        // KB节点保持在收缩后的轨道半径（ORBIT_KB - SHRINK_DIST）
        const targetR = n.kb_id ? (ORBIT_KB - SHRINK_DIST) : ORBIT_BRANCH
        const dx = n.x - cx
        const dy = n.y - cy
        const dist = Math.sqrt(dx * dx + dy * dy) || 1

        // 径向拉回：把节点拉回目标轨道半径
        const radialDiff = targetR - dist
        n.x += (dx / dist) * radialDiff * PULL_FORCE
        n.y += (dy / dist) * radialDiff * PULL_FORCE
      })

      // ── 呼吸漂移：在当前位置附近轻微浮动 ──
      // 用 sin/cos 加上节点 ID 的偏移，让每个节点的漂移相位不同
      // v4.1: 双频漂移（不同周期叠加更像自然浮动），幅度提升到肉眼可感知但仍克制
      nodes.forEach(n => {
        if (n.is_root || n.x == null) return
        const phase = (n.id.charCodeAt(0) || 0) * 0.1
        const t = now * 0.001 + phase
        n.x += Math.sin(t * 0.6) * 0.22 + Math.sin(t * 1.7) * 0.1
        n.y += Math.cos(t * 0.45) * 0.22 + Math.cos(t * 1.3) * 0.1
      })

      schedule()
      requestAnimationFrame(tick)
    }

    requestAnimationFrame(tick)
  }

  let brainImg = null
  let brainImgLoading = false
  function getBrainImg() {
    if (brainImg) return brainImg
    if (brainImgLoading) return null
    brainImgLoading = true
    const img = new Image()
    img.onload = () => { brainImg = img; schedule() }
    img.src = '/brain.png'
    return null
  }

  function init() {
    const host = hostRef.value
    if (!host) return
    host.innerHTML = ''
    const dpr = window.devicePixelRatio || 1
    canvas = document.createElement('canvas')
    canvas.width = host.clientWidth * dpr
    canvas.height = host.clientHeight * dpr
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    host.appendChild(canvas)
    ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    const zoom = d3.zoom().scaleExtent([0.25, 3]).on('zoom', e => { transform = e.transform; schedule() })
    d3.select(canvas).call(zoom)

    d3.select(canvas)
      .on('click', e => {
        const p = screenToWorld(e)
        const n = hitTest(p.x, p.y)
        if (n) {
          if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; onNodeDblClick?.(n) }
          else { clickTimer = setTimeout(() => { clickTimer = null; onNodeClick?.(n) }, 280) }
        } else {
          onCanvasClick?.()
        }
      })
      .on('contextmenu', e => {
        e.preventDefault()
        const p = screenToWorld(e)
        const n = hitTest(p.x, p.y)
        if (n) onNodeRightClick?.(n, e.clientX, e.clientY)
        else onCanvasRightClick?.(e.clientX, e.clientY)
      })

    schedule()
  }

  function screenToWorld(e) {
    const r = canvas.getBoundingClientRect()
    return { x: (e.clientX - r.left - transform.x) / transform.k, y: (e.clientY - r.top - transform.y) / transform.k }
  }

  function hitTest(wx, wy) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]; if (n.x == null || n.y == null) continue
      const r = n.is_root ? 48 : (!n.kb_id ? 36 : 30)
      if ((wx - n.x) ** 2 + (wy - n.y) ** 2 < r * r) return n
    }
    return null
  }

  function updateData(_nodes, _links) {
    nodes = _nodes.map(n => ({ ...n }))
    links = _links.map(l => ({ ...l }))

    const host = hostRef.value
    const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
    const cx = cw / 2, cy = ch / 2

    const root = nodes.find(n => n.is_root)
    const branches = nodes.filter(n => !n.kb_id && !n.is_root)
    const kbs = nodes.filter(n => n.kb_id)

    if (root) {
      root.x = cx
      root.y = cy
    }

    // 分支节点：左右平衡分布在 ORBIT_BRANCH 轨道上
    const getBranchAngle = (i, total) => {
      const leftCount = Math.ceil(total / 2)
      const rightCount = total - leftCount
      if (i < leftCount) {
        const startAngle = -Math.PI * 5 / 6
        const endAngle = -Math.PI / 6
        const range = endAngle - startAngle
        return startAngle + (i / Math.max(leftCount - 1, 1)) * range
      } else {
        const startAngle = Math.PI / 6
        const endAngle = Math.PI * 5 / 6
        const range = endAngle - startAngle
        const rightIndex = i - leftCount
        return startAngle + (rightIndex / Math.max(rightCount - 1, 1)) * range
      }
    }

    branches.forEach((b, i) => {
      const angle = getBranchAngle(i, branches.length)
      b._angle = angle
      b.x = cx + Math.cos(angle) * ORBIT_BRANCH
      b.y = cy + Math.sin(angle) * ORBIT_BRANCH
    })

    // KB 节点：基于父分支节点的角度，在 ORBIT_KB 轨道外侧扇形展开
    branches.forEach((branch) => {
      const branchKbs = kbs.filter(k => {
        const link = links.find(l => l.target_id === k.id && l.source_id === branch.id)
        return !!link
      })
      if (branchKbs.length === 0) return

      const baseAngle = branch._angle
      const spread = Math.PI * 0.35
      const kbCount = branchKbs.length
      const kbAngleStep = spread / Math.max(kbCount, 1)
      const kbStartAngle = baseAngle - spread / 2 + kbAngleStep / 2

      branchKbs.forEach((kb, ki) => {
        const angle = kbStartAngle + kbAngleStep * ki
        kb.x = cx + Math.cos(angle) * ORBIT_KB
        kb.y = cy + Math.sin(angle) * ORBIT_KB
      })
    })

    // 孤儿 KB（直接连根）：左右平衡分布
    const orphanKbs = kbs.filter(k => {
      const link = links.find(l => l.target_id === k.id)
      return !link || (link.source_id === root?.id)
    })
    orphanKbs.forEach((kb, i) => {
      const angle = getBranchAngle(i, orphanKbs.length)
      kb.x = cx + Math.cos(angle) * ORBIT_KB
      kb.y = cy + Math.sin(angle) * ORBIT_KB
    })

    startEnterAnimation()
    schedule()
  }

  function schedule() {
    if (!rafId) rafId = requestAnimationFrame(() => { rafId = null; draw() })
  }

  function draw() {
    if (!ctx || !canvas) return
    const host = hostRef.value
    const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
    const cx = cw / 2, cy = ch / 2
    const dpr = window.devicePixelRatio || 1
    const isSettled = !enterAnimating

    ctx.save(); ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, cw, ch)
    ctx.translate(transform.x, transform.y); ctx.scale(transform.k, transform.k)

    // ── 轨道虚线（仅装饰）──
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 8])
    ctx.beginPath(); ctx.arc(cx, cy, ORBIT_BRANCH, 0, Math.PI * 2); ctx.stroke()
    ctx.beginPath(); ctx.arc(cx, cy, ORBIT_KB, 0, Math.PI * 2); ctx.stroke()
    ctx.setLineDash([])

    // ── 边 ──
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'; ctx.lineWidth = 1.5
    links.forEach(l => {
      const s = nodes.find(n => n.id === l.source_id), t = nodes.find(n => n.id === l.target_id)
      if (!s || !t || s.x == null || t.x == null) return
      const sp = getEnterProgress(s), tp = getEnterProgress(t)
      if (sp < 0.01 || tp < 0.01) return
      ctx.globalAlpha = Math.min(sp, tp)
      const sx = s.is_root || isSettled ? s.x : cx + (s.x - cx) * sp
      const sy = s.is_root || isSettled ? s.y : cy + (s.y - cy) * sp
      const tx = t.is_root || isSettled ? t.x : cx + (t.x - cx) * tp
      const ty = t.is_root || isSettled ? t.y : cy + (t.y - cy) * tp
      ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(tx, ty); ctx.stroke()
    })
    ctx.globalAlpha = 1

    // ── 节点 ──
    nodes.forEach(n => {
      const prog = getEnterProgress(n)
      if (prog < 0.01) return
      const targetX = n.x || cx, targetY = n.y || cy
      const x = n.is_root || isSettled ? targetX : cx + (targetX - cx) * prog
      const y = n.is_root || isSettled ? targetY : cy + (targetY - cy) * prog
      const isBranch = !n.kb_id && !n.is_root
      const isSelected = n.id === selectedNodeId
      const baseR = n.is_root ? 48 : isBranch ? 36 : 30
      const r = baseR * (isSettled ? 1 : prog)
      if (r < 0.5) return

      ctx.globalAlpha = isSettled ? 1 : prog

      // 选中发光 — v4.1: 呼吸脉冲（半径与透明度随时间缓动，而非静态圆）
      if (isSelected) {
        const pulse = 0.5 + 0.5 * Math.sin(performance.now() * 0.0035)
        ctx.beginPath(); ctx.arc(x, y, r + 7 + pulse * 7, 0, Math.PI * 2)
        ctx.fillStyle = isBranch
          ? `rgba(111, 191, 130, ${(0.16 + 0.18 * pulse).toFixed(3)})`
          : `rgba(30, 107, 64, ${(0.12 + 0.16 * pulse).toFixed(3)})`
        ctx.fill()
        ctx.beginPath(); ctx.arc(x, y, r + 2, 0, Math.PI * 2)
        ctx.strokeStyle = isBranch ? 'rgba(200, 245, 215, 0.6)' : 'rgba(120, 220, 160, 0.5)'
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      if (n.is_root) {
        const img = getBrainImg()
        if (img) {
          const w = r * 2.4
          const h = w * (1678 / 1889)
          ctx.drawImage(img, x - w / 2, y - h / 2, w, h)
        } else {
          ctx.fillStyle = '#2D8C4E'
          ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill()
        }
      } else {
        // 分支/知识库节点
        ctx.fillStyle = isBranch ? '#0d9b2e' : '#1E6B40'
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill()

        ctx.strokeStyle = isBranch ? 'rgba(170, 235, 190, 0.55)' : 'rgba(60, 182, 110, 0.4)'
        ctx.lineWidth = 1.5
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke()

        // Emoji
        const fs = isBranch ? 20 : 16
        ctx.font = `${fs}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
        ctx.fillStyle = '#FFFFFF'
        ctx.fillText(n.icon || '📁', x, y)
      }

      // 名称
      const name = (n.name || '').length > 10 ? (n.name || '').slice(0, 10) + '..' : (n.name || '')
      ctx.font = `${n.is_root ? 14 : 13}px "PingFang SC","Microsoft YaHei",sans-serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      ctx.fillStyle = n.is_root ? 'rgba(255, 255, 255, 0.9)' : isBranch ? 'rgba(232, 250, 238, 0.92)' : 'rgba(220, 240, 230, 0.85)'
      ctx.fillText(name, x, y + r + 10)
    })
    ctx.globalAlpha = 1
    ctx.restore()
  }

  function getNodeScreenInfo(nodeId) {
    const n = nodes.find(x => x.id === nodeId)
    if (!n || n.x == null || n.y == null) return null
    const rect = canvas?.getBoundingClientRect()
    if (!rect) return null
    const screenX = rect.left + n.x * transform.k + transform.x
    const screenY = rect.top + n.y * transform.k + transform.y
    const isBranch = !n.kb_id && !n.is_root
    const baseR = n.is_root ? 48 : isBranch ? 36 : 30
    const radius = baseR * transform.k
    let color = '#1E6B40'
    if (n.is_root) color = '#2D8C4E'
    else if (isBranch) color = '#6FBF82'
    return { x: screenX, y: screenY, radius, color, name: n.name, is_root: n.is_root, kb_id: n.kb_id }
  }

  function resize() {
    if (!canvas || !hostRef.value) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = hostRef.value.clientWidth * dpr
    canvas.height = hostRef.value.clientHeight * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    schedule()
  }

  function destroy() {
    nodes = []; links = []
    forceLoopRunning = false
    enterAnimating = false
    if (rafId) cancelAnimationFrame(rafId)
    if (clickTimer) clearTimeout(clickTimer)
  }

  function setSelectedNode(nodeId) {
    selectedNodeId = (selectedNodeId === nodeId) ? null : nodeId
    schedule()
  }

  // v4.1 (#70): 可见性控制 — 画布隐藏/页面后台时暂停力循环与重绘（隐藏 canvas
  // 不再以 60fps 空转），恢复可见时续跑
  function pauseRender() {
    forceLoopRunning = false
  }

  function resumeRender() {
    if (!forceLoopRunning) startGentleForceLoop()
    schedule()
  }

  return { init, updateData, resize, destroy, getNodeScreenInfo, setSelectedNode, pauseRender, resumeRender }
}
