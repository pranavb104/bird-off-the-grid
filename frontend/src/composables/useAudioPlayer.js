/* eslint-disable */
import { ref, onUnmounted } from 'vue'
import { useLogger } from './useLogger'

export function useAudioPlayer() {
    const logger = useLogger('useAudioPlayer')

    // State
    const currentPlayingId = ref(null)
    const audioElement = ref(null)
    const isLoading = ref(false)
    const error = ref(null)

    const stopAudio = () => {
        if (!audioElement.value) return

        try {
            audioElement.value.pause()
            audioElement.value.src = ''
        } catch (err) {
            logger.warn('Error stopping audio:', err)
        }

        audioElement.value = null
        currentPlayingId.value = null
        isLoading.value = false
    }

    const togglePlay = async (id, audioUrl) => {
        if (!id || !audioUrl) {
            return false
        }

        // If same item is playing, stop it
        if (currentPlayingId.value === id) {
            stopAudio()
            return false
        }

        // Stop any currently playing audio
        stopAudio()

        // Create new audio element
        const audio = new Audio(audioUrl)
        audioElement.value = audio
        currentPlayingId.value = id
        isLoading.value = true
        error.value = null

        // Set up event handlers
        audio.onended = () => {
            if (currentPlayingId.value === id) {
                stopAudio()
            }
        }

        audio.onerror = (event) => {
            if (currentPlayingId.value === id) {
                error.value = 'Audio playback error'
                stopAudio()
            }
        }

        // Start playback
        try {
            await audio.play()
            if (currentPlayingId.value === id) {
                isLoading.value = false
            }
            return true
        } catch (err) {
            if (currentPlayingId.value === id) {
                error.value = err.message || 'Failed to play audio'
                stopAudio()
            }
            return false
        }
    }

    const isPlaying = (id) => currentPlayingId.value === id
    const clearError = () => error.value = null

    onUnmounted(() => {
        stopAudio()
    })

    return {
        currentPlayingId,
        isLoading,
        error,
        togglePlay,
        stopAudio,
        isPlaying,
        clearError
    }
}
