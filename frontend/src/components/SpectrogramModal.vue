<template>
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isVisible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--color-text)]/80"
      @click.self="close"
    >
      <div class="relative max-w-[95vw]">
        <div class="d-card relative flex flex-col">
          <DitherShadow :intensity="0.55" />

          <!-- Image region -->
          <div class="relative">
            <img
              :src="imageUrl"
              :alt="alt"
              class="spectrogram-img block w-full max-h-[80vh] object-contain"
            >
            <div
              v-if="audioUrl"
              class="absolute top-0 bottom-0 w-0.5 bg-[var(--color-text)] opacity-90 pointer-events-none transition-none"
              :style="{ left: (progress * 100) + '%' }"
            />
          </div>

          <!-- Control bar — cream, on-theme -->
          <div
            v-if="audioUrl"
            class="flex items-center gap-3 px-3 py-2 border-t-[1.5px] border-[var(--color-border)] bg-[var(--color-card)]"
          >
            <button
              @click="toggleAudio"
              class="d-btn !p-1.5 flex items-center justify-center"
              :title="isPlaying ? 'Pause' : 'Play'"
            >
              <svg v-if="isPlaying" class="w-3 h-3" viewBox="0 0 14 14" fill="currentColor">
                <rect x="2" y="1" width="3.5" height="12" />
                <rect x="8.5" y="1" width="3.5" height="12" />
              </svg>
              <svg v-else class="w-3 h-3" viewBox="0 0 14 14" fill="currentColor">
                <polygon points="3,1 12,7 3,13" />
              </svg>
            </button>

            <div class="relative flex-1 h-[18px] cursor-pointer" @click="seekTo">
              <div class="absolute inset-0 border-[1.5px] border-[var(--color-border)] rounded-[2px] bg-[var(--color-card)] overflow-hidden">
                <div
                  class="h-full bg-[var(--color-text)]"
                  :style="{ width: (progress * 100) + '%' }"
                ></div>
              </div>
            </div>

            <span class="time-label">
              {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            </span>
          </div>

          <!-- No-audio state -->
          <div
            v-else
            class="px-3 py-2 border-t-[1.5px] border-[var(--color-border)] bg-[var(--color-card)] flex items-center justify-center"
          >
            <span class="no-audio-label">No audio available</span>
          </div>

          <audio
            v-if="audioUrl"
            ref="audioEl"
            :src="audioUrl"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onMetadata"
            @ended="onEnded"
          />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script>
import { ref, watch, nextTick } from 'vue'
import DitherShadow from './DitherShadow.vue'

export default {
  name: 'SpectrogramModal',
  components: { DitherShadow },
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    imageUrl: {
      type: String,
      required: true
    },
    alt: {
      type: String,
      default: 'Spectrogram'
    },
    audioUrl: {
      type: String,
      default: ''
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const audioEl = ref(null)
    const isPlaying = ref(false)
    const progress = ref(0)
    const currentTime = ref(0)
    const duration = ref(0)

    const close = () => {
      emit('close')
    }

    const toggleAudio = () => {
      if (!audioEl.value) return
      if (isPlaying.value) {
        audioEl.value.pause()
        isPlaying.value = false
      } else {
        audioEl.value.play()
          .then(() => { isPlaying.value = true })
          .catch(e => { console.error('Error playing audio', e) })
      }
    }

    const seekTo = (e) => {
      if (!audioEl.value || !duration.value) return
      const rect = e.currentTarget.getBoundingClientRect()
      const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
      audioEl.value.currentTime = ratio * duration.value
    }

    const onTimeUpdate = () => {
      if (!audioEl.value) return
      const audio = audioEl.value
      progress.value = audio.duration ? audio.currentTime / audio.duration : 0
      currentTime.value = audio.currentTime
    }

    const onMetadata = () => {
      if (!audioEl.value) return
      duration.value = audioEl.value.duration
    }

    const onEnded = () => {
      isPlaying.value = false
      progress.value = 0
      currentTime.value = 0
    }

    const formatTime = (s) => {
      if (!s || isNaN(s)) return '0:00'
      const mins = Math.floor(s / 60)
      const secs = Math.floor(s % 60)
      return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const resetAudioState = () => {
      if (audioEl.value) {
        audioEl.value.pause()
        audioEl.value.currentTime = 0
      }
      isPlaying.value = false
      progress.value = 0
      currentTime.value = 0
      duration.value = 0
    }

    watch(() => props.isVisible, async (visible) => {
      if (visible && props.audioUrl) {
        await nextTick()
        if (audioEl.value) {
          audioEl.value.play()
            .then(() => { isPlaying.value = true })
            .catch(e => { console.error('Autoplay blocked:', e) })
        }
      } else if (!visible) {
        resetAudioState()
      }
    })

    return {
      audioEl,
      isPlaying,
      progress,
      currentTime,
      duration,
      close,
      toggleAudio,
      seekTo,
      onTimeUpdate,
      onMetadata,
      onEnded,
      formatTime
    }
  }
}
</script>

<style scoped>
.spectrogram-img {
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}

.time-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  color: var(--color-text);
}

.no-audio-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}
</style>
