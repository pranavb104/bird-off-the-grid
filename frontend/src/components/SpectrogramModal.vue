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
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      @click.self="close"
    >
      <div class="relative max-w-full max-w-[95vw]">
        <!-- Image + overlay container -->
        <div class="relative bg-gray-900 rounded-lg shadow-xl overflow-hidden">
          <img
            :src="imageUrl"
            :alt="alt"
            class="block w-full max-h-[80vh] object-contain"
          >

          <!-- Progress line — only when audio is present and playing/loaded -->
          <div
            v-if="audioUrl"
            class="absolute top-0 bottom-0 w-0.5 bg-green-400 opacity-90 pointer-events-none transition-none"
            :style="{ left: (progress * 100) + '%' }"
          />

          <!-- Audio control bar -->
          <div
            v-if="audioUrl"
            class="absolute bottom-0 left-0 right-0 flex items-center gap-2 px-3 py-2 bg-black/60"
          >
            <button
              @click="toggleAudio"
              class="text-white hover:text-green-400 transition-colors focus:outline-none w-5 flex items-center justify-center"
            >
              <font-awesome-icon :icon="isPlaying ? ['fas', 'pause'] : ['fas', 'play']" />
            </button>
            <div class="flex-1 h-1 bg-white/30 rounded-full overflow-hidden cursor-pointer" @click="seekTo">
              <div class="h-full bg-green-400 rounded-full" :style="{ width: (progress * 100) + '%' }"></div>
            </div>
            <span class="text-white text-xs whitespace-nowrap">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          </div>

          <!-- No-audio indicator when modal opened without audio -->
          <div
            v-else
            class="absolute bottom-0 left-0 right-0 flex items-center justify-center px-3 py-1.5 bg-black/40"
          >
            <span class="text-gray-300 text-xs">No audio available</span>
          </div>

          <!-- Hidden audio element -->
          <audio
            v-if="audioUrl"
            ref="audioEl"
            :src="audioUrl"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onMetadata"
            @ended="onEnded"
          />
        </div>

        <!-- Close button (outside top-right corner) -->
        <button
          @click="close"
          class="absolute -top-2 -right-2 sm:-top-3 sm:-right-3 p-1 sm:p-1.5 rounded-full bg-gray-800 text-gray-200 hover:bg-gray-700 hover:text-white transition-colors focus:outline-none shadow-lg"
          title="Close"
        >
          <svg class="h-4 w-4 sm:h-5 sm:w-5" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </Transition>
</template>

<script>
import { ref, watch, nextTick } from 'vue'

export default {
  name: 'SpectrogramModal',
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
