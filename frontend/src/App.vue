<template>
  <router-view />
  <!--
    节点展开遮罩
    原理：全屏 fixed 层，mask-image 用 radial-gradient 从节点位置挖洞。
    洞是圆形，但被视口自然裁剪 — 碰到屏幕边缘的部分自动"压平"为矩形边。
    随着半径增大，圆的四个弧段依次贴合矩形的四条边，自然形成 圆→矩形 的过渡。
    同时 opacity 从 1 渐变到 0，颜色逐渐变淡，露出下方的 KB 页面。
  -->
  <div
    v-if="transitionAnim.visible"
    class="node-expand-overlay"
    :style="transitionAnim.overlayStyle"
  />
</template>

<script setup>
import { reactive, provide } from 'vue'

const transitionAnim = reactive({
  visible: false,
  overlayStyle: {},
  _raf: null,
})

/**
 * 将 hex 颜色与白色按比例混合
 */
function blendColor(hex, weight) {
  let r, g, b
  if (hex.startsWith('#') && hex.length === 7) {
    r = parseInt(hex.slice(1, 3), 16)
    g = parseInt(hex.slice(3, 5), 16)
    b = parseInt(hex.slice(5, 7), 16)
  } else {
    r = 30; g = 107; b = 64
  }
  r = Math.round(r * weight + 255 * (1 - weight))
  g = Math.round(g * weight + 255 * (1 - weight))
  b = Math.round(b * weight + 255 * (1 - weight))
  return `rgb(${r}, ${g}, ${b})`
}

/**
 * v4.2: 连续的展开缓动 — easeOutQuart 主曲线 + 前 10% 软启动。
 * 修复旧版分段指数曲线在 t=0.4 处的不连续跳变（半径会突然回缩），
 * 单条幂曲线全程连续可导，展开"一气呵成"。
 */
function easeExpand(t) {
  if (t >= 1) return 1
  const easeOutQuart = 1 - Math.pow(1 - t, 4)
  const softStart = Math.min(1, t / 0.1)   // 前 10% 从静止平滑拉起，避免瞬间满速的生硬感
  return easeOutQuart * (0.72 + 0.28 * softStart)
}

/** smoothstep — S 形平滑过渡（用于透明度等） */
function smoothstep(t) {
  const x = Math.min(Math.max(t, 0), 1)
  return x * x * (3 - 2 * x)
}

/**
 * 启动节点展开动画
 *
 * 核心：mask-image: radial-gradient(circle at Xpx Ypx, transparent 0px, transparent Rpx, black Rpx, black 100%)
 *   - transparent = 可见（遮罩颜色）
 *   - black = 被遮盖（透明洞）
 *   - 洞是完美的圆，但因为是全屏 div，圆超出视口的部分自然被裁剪
 *   - 随半径增大，圆弧碰到屏幕四边 → 被裁为平直边 → 圆自然变矩形
 *
 * @param {number} x - 节点中心屏幕 X（px）
 * @param {number} y - 节点中心屏幕 Y（px）
 * @param {string} color - 节点颜色（hex）
 */
function startNodeExpand(x, y, color) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const nodeColor = color || '#1E6B40'
  // 对角线距离，圆半径达到此值时完全覆盖全屏
  const maxR = Math.sqrt(vw * vw + vh * vh)
  // 混合色用于径向渐变中心发光
  const glowColor = blendColor(nodeColor, 0.85)

  // 初始状态：洞半径 = 0，完全不透明，无模糊
  transitionAnim.overlayStyle = {
    '--node-color': nodeColor,
    '--glow-color': glowColor,
    '--cx': x + 'px',
    '--cy': y + 'px',
    maskImage: buildMask(x, y, 0),
    WebkitMaskImage: buildMask(x, y, 0),
    opacity: '1',
    backdropFilter: 'blur(0px)',
    WebkitBackdropFilter: 'blur(0px)',
  }
  transitionAnim.visible = true

  const duration = 950 // v4.2: 1400 → 950ms，利落不拖沓
  const startTime = performance.now()
  // 软化边缘宽度：随展开推进收窄（起笔 90px 光晕边 → 末段 24px），圆洞边缘柔和
  const featherStart = 90, featherEnd = 24

  function animate(now) {
    const elapsed = now - startTime
    const rawT = Math.min(elapsed / duration, 1)

    // ── 半径：连续缓动驱动 ──
    const t = easeExpand(rawT)
    const radius = maxR * t

    // ── mask：圆洞扩大 + 羽化边缘（不再是生硬的圆弧切割）──
    const feather = featherStart + (featherEnd - featherStart) * smoothstep(rawT)
    const mask = buildMask(x, y, radius, feather)

    // ── opacity：单一 smoothstep 曲线（22% 后开始平滑淡出，替代旧三段折线）──
    const opacity = 1 - smoothstep((rawT - 0.22) / 0.78)

    // ── blur：正弦单峰（中段景深最大，起止为 0，全程连续，替代旧四段折线）──
    const blur = 11 * Math.sin(Math.PI * Math.min(rawT / 0.94, 1))

    // ── 中心辉光：前 220ms 轻微增亮（"点亮"节点的瞬间反馈）后随整体淡出 ──
    const glowBoost = rawT < 0.23 ? smoothstep(rawT / 0.23) * 0.5 : 0

    transitionAnim.overlayStyle = {
      '--node-color': nodeColor,
      '--glow-color': glowColor,
      '--glow-boost': String(glowBoost),
      '--cx': x + 'px',
      '--cy': y + 'px',
      maskImage: mask,
      WebkitMaskImage: mask,
      opacity: String(opacity),
      backdropFilter: `blur(${blur.toFixed(1)}px)`,
      WebkitBackdropFilter: `blur(${blur.toFixed(1)}px)`,
    }

    if (rawT < 1) {
      transitionAnim._raf = requestAnimationFrame(animate)
    }
  }

  transitionAnim._raf = requestAnimationFrame(animate)
}

/**
 * 构建 mask-image 的 radial-gradient 值
 * transparent = 可见（遮罩颜色显示），black = 不可见（洞/透明）
 *
 * @param {number} cx - 圆心 X（px，相对于视口）
 * @param {number} cy - 圆心 Y（px，相对于视口）
 * @param {number} r  - 圆洞半径（px）
 */
function buildMask(cx, cy, r, feather = 40) {
  // v4.2: 洞边缘加羽化渐变带（transparent → black 平滑过渡），
  // 展开边缘呈柔和光晕而非生硬圆弧
  const clampedR = Math.max(0, r)
  const inner = clampedR
  const outer = clampedR + feather
  const mid = inner + feather * 0.45
  return `radial-gradient(circle at ${cx.toFixed(1)}px ${cy.toFixed(1)}px, transparent 0px, transparent ${inner.toFixed(1)}px, rgba(0,0,0,0.4) ${mid.toFixed(1)}px, rgba(0,0,0,1) ${outer.toFixed(1)}px)`
}

function hideNodeExpand() {
  if (transitionAnim._raf) {
    cancelAnimationFrame(transitionAnim._raf)
    transitionAnim._raf = null
  }
  // 加速淡出：不是瞬间消失，而是快速将 opacity 降到 0
  if (transitionAnim.visible) {
    const style = transitionAnim.overlayStyle
    const startOpacity = parseFloat(style.opacity) || 0.5
    const fadeStart = performance.now()
    const fadeDuration = 200 // 200ms 快速淡出

    const fadeOut = (now) => {
      const t = Math.min((now - fadeStart) / fadeDuration, 1)
      const eased = 1 - (1 - t) * (1 - t) // ease-out
      transitionAnim.overlayStyle = {
        ...style,
        opacity: String(startOpacity * (1 - eased)),
        backdropFilter: `blur(${(1 - eased) * 3}px)`,
        WebkitBackdropFilter: `blur(${(1 - eased) * 3}px)`,
      }
      if (t < 1) {
        transitionAnim._raf = requestAnimationFrame(fadeOut)
      } else {
        transitionAnim.visible = false
      }
    }
    transitionAnim._raf = requestAnimationFrame(fadeOut)
  }
}

provide('pageTransition', { startNodeExpand, hideNodeExpand })
</script>

<style>
/*
 * 节点展开遮罩 — 全屏 fixed 层
 *
 * 背景用径向渐变：中心稍亮（--glow-color），外围为节点原色（--node-color）。
 * mask-image 用 radial-gradient 挖圆形洞，洞被视口自然裁剪：
 *   - 小半径时 = 圆形遮罩
 *   - 圆弧碰到屏幕边缘 → 被裁为平直边
 *   - 四条弧段依次贴合四条边 → 自然变成矩形
 * opacity 从 1 → 0，逐渐露出下方的 KB 页面。
 * backdrop-filter: blur() 在中间段增加景深效果。
 */
.node-expand-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  background:
    radial-gradient(
      circle at var(--cx) var(--cy),
      rgba(255, 255, 255, calc(var(--glow-boost, 0) * 0.22)) 0%,
      transparent 18%
    ),
    radial-gradient(
      circle at var(--cx) var(--cy),
      var(--glow-color) 0%,
      var(--node-color) 40%,
      var(--node-color) 100%
    );
  will-change: mask-image, opacity, backdrop-filter;
}
</style>
