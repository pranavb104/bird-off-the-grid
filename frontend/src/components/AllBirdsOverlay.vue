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
      class="fixed inset-0 z-50 bg-[var(--color-background)] flex flex-col"
    >
      <!-- Top bar -->
      <header class="overlay-topbar">
        <button
          type="button"
          class="topbar-btn"
          @click="onBack"
          :aria-label="selectedBird ? 'Back to list' : 'Close overlay'"
        >
          <span aria-hidden="true">←</span>
        </button>
        <div class="overlay-titles">
          <h2 class="font-['IBM_Plex_Mono'] uppercase tracking-widest text-base lg:text-lg text-[var(--color-text)]">
            {{ selectedBird ? selectedBird.common_name : 'All Recorded Birds' }}
          </h2>
          <p v-if="!selectedBird" class="text-xs text-[var(--color-text-muted)] mt-1 font-['IBM_Plex_Mono']">
            {{ species.length }} species &middot; {{ totalCount }} detection{{ totalCount === 1 ? '' : 's' }}
          </p>
          <p v-else class="text-xs italic text-[var(--color-text-secondary)] mt-1 font-['IBM_Plex_Mono']">
            {{ selectedBird.scientific_name }}
          </p>
        </div>
        <button
          type="button"
          class="topbar-btn"
          @click="$emit('close')"
          aria-label="Close overlay"
        >
          <span aria-hidden="true">×</span>
        </button>
      </header>

      <!-- List view -->
      <div
        v-if="!selectedBird"
        class="flex-1 overflow-y-auto px-4 lg:px-6 py-6 bg-[var(--color-background)]"
      >
        <ul v-if="species.length" class="space-y-4 max-w-3xl mx-auto">
          <li
            v-for="bird in species"
            :key="bird.scientific_name"
            class="d-card flex items-center gap-4 p-3 cursor-pointer transition-transform hover:-translate-y-px"
            @click="openBird(bird)"
          >
            <DitherShadow />
            <img
              :src="imageUrls[bird.scientific_name] || '/default_bird.svg'"
              :alt="bird.common_name"
              @error="onImgError(bird)"
              :style="{ imageRendering: pixelated(bird) ? 'pixelated' : 'auto' }"
              class="w-20 h-20 lg:w-24 lg:h-24 object-cover rounded-full border-[1.5px] border-[var(--color-border)] shrink-0"
            >
            <div class="flex-1 min-w-0">
              <div class="text-base lg:text-lg font-semibold text-[var(--color-text)] truncate">
                {{ bird.common_name }}
              </div>
              <div class="text-sm italic text-[var(--color-text-secondary)] truncate">
                {{ bird.scientific_name }}
              </div>
            </div>
            <div class="relative w-16 h-16 lg:w-20 lg:h-20 shrink-0">
              <img :src="starUrl" alt="" class="w-full h-full" aria-hidden="true">
              <span
                class="absolute inset-0 flex items-center justify-center font-['IBM_Plex_Mono'] font-bold text-[var(--color-text)]"
                :class="bird.count >= 100 ? 'text-sm lg:text-base' : 'text-base lg:text-lg'"
              >
                {{ bird.count }}
              </span>
            </div>
          </li>
        </ul>
        <p v-else class="text-center text-[var(--color-text-muted)] py-12">
          No species recorded yet.
        </p>
      </div>

      <!-- Detail view -->
      <div
        v-else
        class="flex-1 overflow-y-auto px-4 lg:px-6 py-6 bg-[var(--color-background)]"
      >
        <div class="max-w-3xl mx-auto">
          <p class="d-section-label">Latest 5 recordings</p>

          <p v-if="loadingRecordings" class="text-center text-[var(--color-text-muted)] py-12">
            Loading recordings…
          </p>
          <p v-else-if="recordingsError" class="text-center text-[var(--color-error)] py-12">
            {{ recordingsError }}
          </p>
          <p v-else-if="!recordings.length" class="text-center text-[var(--color-text-muted)] py-12">
            No recordings yet for this species.
          </p>
          <ul v-else class="space-y-3">
            <li
              v-for="r in recordings"
              :key="r.id"
              class="d-card flex items-center justify-between gap-4 p-4 cursor-pointer transition-transform hover:-translate-y-px"
              @click="$emit('play-detection', r)"
            >
              <DitherShadow />
              <div class="flex flex-col min-w-0">
                <span class="font-['IBM_Plex_Mono'] text-sm lg:text-base text-[var(--color-text)]">
                  {{ formatDate(r.date) }}
                </span>
                <span class="font-['IBM_Plex_Mono'] text-xs text-[var(--color-text-secondary)] mt-1">
                  {{ r.time }}
                </span>
              </div>
              <span class="font-['IBM_Plex_Mono'] text-sm text-[var(--color-text-secondary)] shrink-0">
                {{ Math.round((r.confidence || 0) * 100) }}%
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script>
import { ref, computed, watch } from 'vue'
import birdImages from '@/services/birdImages'
import api from '@/services/api'
import DitherShadow from './DitherShadow.vue'
import starUrl from '@/assets/star.png'

export default {
  name: 'AllBirdsOverlay',
  components: { DitherShadow },
  props: {
    isVisible: { type: Boolean, default: false },
    species: { type: Array, default: () => [] },
  },
  emits: ['close', 'play-detection'],
  setup(props, { emit }) {
    const imageUrls = ref({})
    const failedOnce = ref({})

    const selectedBird = ref(null)
    const recordings = ref([])
    const loadingRecordings = ref(false)
    const recordingsError = ref(null)

    const totalCount = computed(() =>
      props.species.reduce((s, b) => s + (b.count || 0), 0)
    )

    const resolveInitial = (bird) => {
      const pixel = bird.common_name ? birdImages[bird.common_name] : null
      if (pixel) return pixel
      const speciesParam = bird.common_name || bird.scientific_name
      const base = api.defaults.baseURL
      return `${base}/bird-image?species=${encodeURIComponent(speciesParam)}`
    }

    const pixelated = (bird) => {
      const url = imageUrls.value[bird.scientific_name]
      return typeof url === 'string' && url.startsWith('/birds/')
    }

    const onImgError = (bird) => {
      const key = bird.scientific_name
      if (failedOnce.value[key]) return
      failedOnce.value[key] = true
      imageUrls.value[key] = '/default_bird.svg'
    }

    watch(
      () => props.species,
      (list) => {
        const next = {}
        const failed = {}
        for (const bird of list) {
          next[bird.scientific_name] = resolveInitial(bird)
          failed[bird.scientific_name] = false
        }
        imageUrls.value = next
        failedOnce.value = failed
      },
      { immediate: true }
    )

    // Reset the detail view whenever the overlay is hidden so the next open
    // starts back on the list.
    watch(
      () => props.isVisible,
      (open) => {
        if (!open) {
          selectedBird.value = null
          recordings.value = []
          recordingsError.value = null
        }
      }
    )

    const openBird = async (bird) => {
      selectedBird.value = bird
      recordings.value = []
      recordingsError.value = null
      loadingRecordings.value = true
      try {
        const res = await api.get('/detections', {
          params: { species: bird.scientific_name, limit: 5 },
        })
        recordings.value = Array.isArray(res.data) ? res.data : []
      } catch (e) {
        recordingsError.value = 'Failed to load recordings.'
      } finally {
        loadingRecordings.value = false
      }
    }

    const onBack = () => {
      if (selectedBird.value) {
        selectedBird.value = null
        recordings.value = []
        recordingsError.value = null
      } else {
        emit('close')
      }
    }

    const formatDate = (iso) => {
      if (!iso) return ''
      const d = new Date(`${iso}T00:00:00`)
      if (isNaN(d.getTime())) return iso
      return d.toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
      })
    }

    return {
      imageUrls,
      starUrl,
      totalCount,
      pixelated,
      onImgError,
      selectedBird,
      recordings,
      loadingRecordings,
      recordingsError,
      openBird,
      onBack,
      formatDate,
    }
  },
}
</script>

<style scoped>
.overlay-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1.5px solid var(--color-border);
  background: var(--color-background);
}

.overlay-titles {
  flex: 1;
  min-width: 0;
}

.topbar-btn {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1.4rem;
  line-height: 1;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-card);
  color: var(--color-text);
  border: 1.5px solid var(--color-border);
  border-radius: 2px;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 0.08s ease;
}

.topbar-btn:hover {
  transform: translate(-1px, -1px);
}

.topbar-btn:active {
  transform: translate(1px, 1px);
}
</style>
