<template>
  <img
    class="brain-logo"
    :class="{
      'brain-logo--green': variant === 'green',
      'brain-logo--light': variant === 'light',
      'brain-logo--white': variant === 'white'
    }"
    :src="src"
    :style="style"
    alt="brain"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 200
  },
  variant: {
    type: String,
    default: 'green'
  }
})

// v4.1 (#87): 小尺寸自动切换 sm 变体（20KB 级），避免侧栏 44px 图标加载 440KB+ 大图
const src = computed(() => {
  const small = Number(props.size) <= 160
  if (props.variant === 'green') {
    return small ? '/brain-green-sm.png' : '/brain-green.png'
  }
  return small ? '/brain-sm.png' : '/brain.png'
})

const style = computed(() => {
  const s = Number(props.size)
  const ratio = 1678 / 1889
  const h = Math.round(s * ratio)
  return {
    width: `${s}px`,
    height: `${h}px`,
    objectFit: 'contain'
  }
})
</script>

<style scoped lang="scss">
.brain-logo {
  display: block;
}

.brain-logo--light {
  opacity: 0.85;
}

.brain-logo--white {
  opacity: 1;
}
</style>
