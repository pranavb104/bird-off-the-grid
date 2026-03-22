<template>
  <canvas ref="canvasEl" class="dither-drop" :data-intensity="intensity"></canvas>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { renderDitherShadow } from '@/composables/useDither'

export default {
  name: 'DitherShadow',
  props: {
    intensity: {
      type: Number,
      default: 0.55
    }
  },
  setup(props) {
    const canvasEl = ref(null)
    let observer = null

    const render = () => {
      if (!canvasEl.value) return
      renderDitherShadow(canvasEl.value, props.intensity)
    }

    onMounted(() => {
      render()
      const parent = canvasEl.value?.parentElement
      if (parent) {
        observer = new ResizeObserver(() => render())
        observer.observe(parent)
      }
    })

    onUnmounted(() => {
      if (observer) observer.disconnect()
    })

    return { canvasEl }
  }
}
</script>

<style scoped>
.dither-drop {
  position: absolute;
  top: 4px;
  left: 2px;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
  border-radius: inherit;
}
</style>
