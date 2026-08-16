<template>
  <!--
    v4.1 (#87): 通用骨架屏 — 加载态视觉统一（ shimmer 微光动画）
    纯展示组件：lines 行数 / avatar 是否首行圆形 / compact 紧凑模式
  -->
  <div class="app-skeleton" :class="{ 'app-skeleton--compact': compact }" aria-busy="true" aria-label="加载中">
    <div v-if="title" class="skeleton-bar skeleton-title"></div>
    <div v-for="i in lines" :key="i" class="skeleton-row" :style="{ width: rowWidth(i) }">
      <div v-if="avatar && i === 1" class="skeleton-avatar"></div>
      <div class="skeleton-bar"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  lines: { type: Number, default: 4 },
  title: { type: Boolean, default: false },
  avatar: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
})

function rowWidth(i) {
  // 交错宽度更接近真实内容节奏
  const widths = ['100%', '86%', '94%', '72%', '90%', '65%']
  return widths[(i - 1) % widths.length]
}
</script>

<style scoped lang="scss">
.app-skeleton {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.app-skeleton--compact {
  padding: 8px;
  gap: 8px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.skeleton-bar,
.skeleton-avatar,
.skeleton-title {
  background: linear-gradient(
    100deg,
    rgba(46, 125, 80, 0.06) 40%,
    rgba(46, 125, 80, 0.14) 50%,
    rgba(46, 125, 80, 0.06) 60%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s ease-in-out infinite;
  border-radius: 6px;
}

.skeleton-bar {
  flex: 1;
  height: 14px;
}

.skeleton-title {
  height: 20px;
  width: 38%;
  margin-bottom: 4px;
}

.skeleton-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex: none;
}

@keyframes skeleton-shimmer {
  0% { background-position: 120% 0; }
  100% { background-position: -20% 0; }
}

/* 尊重系统"减弱动态效果"设置 */
@media (prefers-reduced-motion: reduce) {
  .skeleton-bar, .skeleton-avatar, .skeleton-title {
    animation: none;
  }
}
</style>
