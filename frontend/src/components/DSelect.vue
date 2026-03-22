<template>
  <div class="d-select-wrap" :class="{ open }" ref="wrapEl">
    <canvas ref="triggerShadow" class="dither-drop" data-intensity="0.55"></canvas>
    <div class="d-select-trigger" @click.stop="toggle">
      <span>{{ selectedText }}</span>
      <span class="arrow">▼</span>
    </div>
    <div class="d-select-panel-wrap">
      <canvas ref="panelShadow" class="d-select-panel-shadow"></canvas>
      <div class="d-select-panel" ref="panelEl">
        <div
          v-for="opt in options"
          :key="opt.value"
          class="d-option"
          :class="{ 'selected-opt': opt.value === modelValue }"
          @click="select(opt)"
        >
          <canvas class="option-dither" ref="optionCanvases"></canvas>
          {{ opt.text }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { renderDitherShadow, renderDitherFill } from '@/composables/useDither'

export default {
  name: 'DSelect',
  props: {
    options: {
      type: Array,
      required: true
    },
    modelValue: {
      type: [String, Number],
      default: ''
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const open = ref(false)
    const wrapEl = ref(null)
    const triggerShadow = ref(null)
    const panelShadow = ref(null)
    const panelEl = ref(null)

    const selectedText = computed(() => {
      const found = props.options.find(o => o.value === props.modelValue)
      return found ? found.text : '— Select —'
    })

    const renderShadows = () => {
      if (triggerShadow.value) {
        renderDitherShadow(triggerShadow.value, 0.55)
      }
    }

    const renderOptionDithers = () => {
      if (!panelEl.value) return
      panelEl.value.querySelectorAll('.d-option').forEach(opt => {
        const canvas = opt.querySelector('canvas.option-dither')
        if (!canvas) return
        const W = opt.offsetWidth || 200
        const H = opt.offsetHeight || 36
        if (W > 0 && H > 0) renderDitherFill(canvas, W, H, 0.88)
      })
      if (panelShadow.value && panelEl.value) {
        const W = panelEl.value.offsetWidth
        const H = panelEl.value.offsetHeight
        if (W > 0 && H > 0) renderDitherShadow(panelShadow.value, 0.6, W, H)
      }
    }

    const toggle = () => {
      open.value = !open.value
      if (open.value) {
        nextTick(() => renderOptionDithers())
      }
    }

    const select = (opt) => {
      emit('update:modelValue', opt.value)
      open.value = false
    }

    const onClickOutside = (e) => {
      if (wrapEl.value && !wrapEl.value.contains(e.target)) {
        open.value = false
      }
    }

    onMounted(() => {
      renderShadows()
      document.addEventListener('click', onClickOutside)
    })

    onUnmounted(() => {
      document.removeEventListener('click', onClickOutside)
    })

    return {
      open,
      wrapEl,
      triggerShadow,
      panelShadow,
      panelEl,
      selectedText,
      toggle,
      select
    }
  }
}
</script>

<style scoped>
.d-select-wrap {
  position: relative;
  display: inline-block;
  width: 100%;
}

.d-select-wrap > canvas.dither-drop {
  position: absolute;
  top: 4px;
  left: 2px;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.d-select-trigger {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  background: var(--color-card);
  color: var(--color-text);
  border: 1.5px solid var(--color-border);
  padding: 10px 36px 10px 14px;
  cursor: pointer;
  border-radius: 2px;
  min-width: 200px;
  position: relative;
  z-index: 2;
  transition: transform 0.08s ease;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.d-select-wrap:hover .d-select-trigger,
.d-select-wrap.open .d-select-trigger {
  transform: translate(-1px, -1px);
}

.arrow {
  font-size: 10px;
  color: var(--color-text);
  transition: transform 0.15s ease;
  pointer-events: none;
  margin-left: 12px;
  flex-shrink: 0;
}

.d-select-wrap.open .arrow {
  transform: rotate(180deg);
}

.d-select-panel-wrap {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 100%;
  display: none;
  z-index: 100;
}

.d-select-wrap.open .d-select-panel-wrap {
  display: block;
}

.d-select-panel-shadow {
  position: absolute;
  top: 4px;
  left: 2px;
  z-index: 98;
  pointer-events: none;
  border-radius: 2px;
}

.d-select-panel {
  position: relative;
  width: 100%;
  background: var(--color-card);
  border: 1.5px solid var(--color-border);
  border-radius: 2px;
  z-index: 100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.d-option {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  padding: 9px 14px;
  cursor: pointer;
  position: relative;
  user-select: none;
  color: var(--color-text);
  border-bottom: 1px solid #ddd;
  isolation: isolate;
  transition: color 0.06s;
}

.d-option:last-child {
  border-bottom: none;
}

.d-option .option-dither {
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.08s ease;
}

.d-option:hover .option-dither,
.d-option.active .option-dither {
  opacity: 1;
}

.d-option:hover,
.d-option.active {
  color: var(--color-card);
}

.d-option.selected-opt {
  font-weight: 700;
}
</style>
