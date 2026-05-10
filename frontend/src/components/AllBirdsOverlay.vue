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
      <!-- Header -->
      <header class="px-6 py-4 border-b-[1.5px] border-[var(--color-border)] bg-[var(--color-background)]">
        <h2 class="font-['IBM_Plex_Mono'] uppercase tracking-widest text-base lg:text-lg text-[var(--color-text)]">
          All Recorded Birds
        </h2>
        <p class="text-xs text-[var(--color-text-muted)] mt-1 font-['IBM_Plex_Mono']">
          {{ species.length }} species &middot; {{ totalCount }} detection{{ totalCount === 1 ? '' : 's' }}
        </p>
      </header>

      <!-- Capture area: this is what gets PDF'd -->
      <div ref="captureArea" class="flex-1 overflow-y-auto px-4 lg:px-6 py-6 bg-[var(--color-background)]">
        <ul v-if="species.length" class="space-y-4 max-w-3xl mx-auto">
          <li
            v-for="bird in species"
            :key="bird.scientific_name"
            class="d-card flex items-center gap-4 p-3"
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

      <!-- Bottom action bar -->
      <footer class="px-6 py-4 border-t-[1.5px] border-[var(--color-border)] bg-[var(--color-background)] flex justify-end gap-3">
        <button class="d-btn outline" @click="$emit('close')">Cancel</button>
        <button
          class="d-btn"
          :disabled="exporting || !species.length"
          @click="exportPdf"
        >
          {{ exporting ? 'Saving...' : 'Save PDF' }}
        </button>
      </footer>
    </div>
  </Transition>
</template>

<script>
import { ref, computed, watch } from 'vue'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
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
  emits: ['close'],
  setup(props) {
    const captureArea = ref(null)
    const exporting = ref(false)
    const imageUrls = ref({})
    const failedOnce = ref({})

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

    const exportPdf = async () => {
      if (!captureArea.value) return
      exporting.value = true
      try {
        const bg = getComputedStyle(document.body)
          .getPropertyValue('--color-background').trim() || '#f0ece3'

        const canvas = await html2canvas(captureArea.value, {
          scale: 2,
          backgroundColor: bg,
          useCORS: true,
          windowWidth: captureArea.value.scrollWidth,
          windowHeight: captureArea.value.scrollHeight,
        })

        const pdf = new jsPDF({ unit: 'pt', format: 'a4' })
        const pageW = pdf.internal.pageSize.getWidth()
        const pageH = pdf.internal.pageSize.getHeight()
        const imgH = (canvas.height * pageW) / canvas.width

        let heightLeft = imgH
        let position = 0
        pdf.addImage(canvas, 'PNG', 0, position, pageW, imgH)
        heightLeft -= pageH
        while (heightLeft > 0) {
          position = heightLeft - imgH
          pdf.addPage()
          pdf.addImage(canvas, 'PNG', 0, position, pageW, imgH)
          heightLeft -= pageH
        }
        const today = new Date().toISOString().slice(0, 10)
        pdf.save(`birds-${today}.pdf`)
      } catch (e) {
        console.error('PDF export failed', e)
      } finally {
        exporting.value = false
      }
    }

    return {
      captureArea,
      exporting,
      imageUrls,
      starUrl,
      totalCount,
      pixelated,
      onImgError,
      exportPdf,
    }
  },
}
</script>
