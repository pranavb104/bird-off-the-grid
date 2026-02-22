<template>
    <div class="dashboard container mx-auto px-4 py-6">
        <h1 class="text-xl font-bold mb-4 text-gray-800 lg:text-3xl lg:mb-6">BirdNET Dashboard</h1>
        
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4">
            <!-- Bird Activity Overview -->
            <div class="bg-white rounded-lg shadow p-4 lg:col-span-3 h-[260px] lg:h-[375px]">
                <h2 class="text-base font-semibold mb-2 text-gray-700 lg:text-lg">Bird Activity Overview</h2>
                <div v-if="!isDataEmpty && !detailedBirdActivityError" class="flex h-[calc(100%-2rem)]">
                    <div class="w-full h-full" :class="isDesktop ? 'lg:w-1/3 lg:pr-2' : ''">
                        <canvas ref="totalObservationsChart" class="h-full w-full"></canvas>
                    </div>
                    <div v-show="isDesktop" class="lg:w-2/3 lg:pl-2 h-full">
                        <canvas ref="hourlyActivityHeatmap" class="h-full w-full"></canvas>
                    </div>
                </div>
                <div v-else-if="detailedBirdActivityError" class="flex items-center justify-center h-[calc(100%-2rem)]">
                    <p class="text-lg text-red-500">{{ detailedBirdActivityError }}</p>
                </div>
                <div v-else class="flex items-center justify-center h-[calc(100%-2rem)]">
                    <p class="text-lg text-gray-500">No bird activity recorded yet for today.</p>
                </div>
            </div>

            <!-- Latest Observation -->
            <div class="bg-white rounded-lg shadow p-4 lg:col-span-2 flex flex-col">
                <h2 class="text-base font-semibold mb-3 text-left text-gray-700 lg:text-lg">Latest Observation</h2>
                <div v-if="latestObservationData && !latestObservationError"
                    class="flex flex-row items-center space-x-3 w-full">
                    <!-- Bird avatar -->
                    <img :src="latestObservationimageUrl" :alt="latestObservationData.common_name"
                        @error="latestObservationimageUrl = '/default_bird.svg'"
                        class="w-14 h-14 object-cover rounded-full border-2 border-gray-200 shrink-0">
                    <!-- Bird info -->
                    <div class="flex-1 min-w-0">
                        <h3 class="text-sm font-semibold text-gray-800 truncate">{{ latestObservationData.common_name }}</h3>
                        <p class="text-xs text-gray-500 italic truncate">{{ latestObservationData.scientific_name }}</p>
                        <p class="text-xs text-gray-400 mt-0.5">{{ formatTimestamp(latestObservationData.date + 'T' + latestObservationData.time) }}</p>
                    </div>
                    <!-- Play button -->
                    <button @click="openLatestWithAudio"
                        class="shrink-0 bg-green-600 hover:bg-green-700 text-white rounded-full flex items-center justify-center w-11 h-11 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-green-300 shadow-md">
                        <font-awesome-icon :icon="['fas', 'play']" class="text-base ml-0.5" />
                    </button>
                </div>
                <p v-else-if="latestObservationError" class="mt-2 text-red-500">{{ latestObservationError }}</p>
                <p v-else class="mt-2 text-gray-500">No observations available yet.</p>
            </div>

            <!-- Observation Summary -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold mb-2 text-gray-700 lg:text-lg">Observation Summary</h2>
                <div v-if="!summaryError">
                    <ul v-if="summaryData && Object.keys(summaryData).length" class="space-y-2 text-sm">
                         <li class="flex justify-between border-b pb-1">
                            <span class="text-gray-600">Total Detections</span>
                            <span class="font-bold text-gray-800">{{ summaryData.total_detections || 0 }}</span>
                        </li>
                         <li class="flex justify-between border-b pb-1">
                            <span class="text-gray-600">Species Count</span>
                            <span class="font-bold text-gray-800">{{ summaryData.unique_species || 0 }}</span>
                        </li>
                    </ul>
                    <p v-else class="text-gray-500">No summary data available.</p>
                </div>
                <p v-else class="text-red-500">{{ summaryError }}</p>
            </div>

            <!-- Recent Observations -->
            <div class="bg-white rounded-lg shadow p-4 lg:col-span-2">
                <h2 class="text-base font-semibold mb-2 text-gray-700 lg:text-lg">Recent Observations</h2>
                <div class="overflow-y-auto max-h-[300px]">
                    <ul v-if="recentObservationsData.length && !recentObservationsError" class="space-y-2">
                        <li v-for="observation in recentObservationsData" :key="observation.id"
                            class="flex items-center justify-between p-2 hover:bg-gray-50 rounded-md transition-colors">
                            <div class="flex items-center space-x-3">
                                <div class="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-500 text-xs">
                                    <font-awesome-icon :icon="['fas', 'feather']" />
                                </div>
                                <div>
                                    <div class="font-medium text-gray-800">{{ observation.common_name }}</div>
                                    <div class="text-xs text-gray-500">
                                        {{ formatTimestamp(observation.date + 'T' + observation.time) }}
                                        <span class="mx-1">•</span>
                                        {{ formatConfidence(observation.confidence) }}
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2">
                                <button @click="togglePlayBirdCall(observation)" class="text-green-600 hover:text-green-700 p-2 rounded-full hover:bg-green-50 transition-colors">
                                    <font-awesome-icon
                                        :icon="currentPlayingId === observation.id ? ['fas', 'pause'] : ['fas', 'play']"
                                        class="h-4 w-4" />
                                </button>
                                <button @click="showSpectrogram(observation)"
                                    class="text-blue-500 hover:text-blue-700 p-2 rounded-full hover:bg-blue-50 transition-colors">
                                    <font-awesome-icon :icon="['fas', 'circle-info']" class="h-4 w-4" />
                                </button>
                            </div>
                        </li>
                    </ul>
                    <p v-else-if="recentObservationsError" class="text-red-500">{{ recentObservationsError }}</p>
                    <p v-else class="text-gray-500 py-4 text-center">No recent observations available.</p>
                </div>
            </div>

            <!-- Hourly Activity Chart -->
            <div v-show="isDesktop" class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold mb-2 text-gray-700 lg:text-lg">Hourly Activity</h2>
                <div v-if="!hourlyBirdActivityError" class="relative h-[220px] w-full">
                    <canvas ref="hourlyActivityChart"></canvas>
                </div>
                <p v-else class="text-red-500">{{ hourlyBirdActivityError }}</p>
            </div>
        </div>

        <!-- Spectrogram Modal -->
        <SpectrogramModal
            :is-visible="isSpectrogramModalVisible"
            :image-url="currentSpectrogramUrl"
            :audio-url="currentAudioUrl"
            alt="Spectrogram"
            @close="isSpectrogramModalVisible = false"
        />

    </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Chart from 'chart.js/auto'
import { MatrixController, MatrixElement } from 'chartjs-chart-matrix'

import { useFetchBirdData } from '@/composables/useFetchBirdData';
import { useBirdCharts } from '@/composables/useBirdCharts';
import { useAudioPlayer } from '@/composables/useAudioPlayer';
import SpectrogramModal from '@/components/SpectrogramModal.vue';
import { getAudioUrl, getSpectrogramUrl } from '@/services/media'

Chart.register(MatrixController, MatrixElement)

export default {
    name: 'dash-board',
    components: {
        SpectrogramModal
    },
    setup() {
        const {
            hourlyBirdActivityData,
            detailedBirdActivityData,
            latestObservationData,
            recentObservationsData,
            summaryData,
            latestObservationimageUrl,

            hourlyBirdActivityError,
            detailedBirdActivityError,
            latestObservationError,
            recentObservationsError,
            summaryError,

            fetchDashboardData
        } = useFetchBirdData();

        const isSpectrogramModalVisible = ref(false)
        const currentSpectrogramUrl = ref('')
        const currentAudioUrl = ref('')
        const hourlyActivityChart = ref(null)
        const totalObservationsChart = ref(null)
        const hourlyActivityHeatmap = ref(null)

        const windowWidth = ref(window.innerWidth)
        const handleResize = () => { windowWidth.value = window.innerWidth }
        const isDesktop = computed(() => windowWidth.value >= 1024)

        const initialLoad = ref(true)

        // Audio player composable
        const {
            currentPlayingId,
            togglePlay: audioTogglePlay
        } = useAudioPlayer()

        // Bird charts composable
        const {
            createTotalObservationsChart: createTotalObsChart,
            createHourlyActivityHeatmap: createHeatmap,
            createHourlyActivityChart: createHourlyChart
        } = useBirdCharts()

        let dataFetchInterval;

        onMounted(async () => {
            window.addEventListener('resize', handleResize)
            await fetchDashboardData();

            // Set up polling
            dataFetchInterval = setInterval(async () => {
                await fetchDashboardData();
                redrawCharts();
            }, 30000); // 30 seconds poll

            redrawCharts();
        });

        onUnmounted(() => {
            window.removeEventListener('resize', handleResize)
            if (dataFetchInterval) clearInterval(dataFetchInterval);
        })

        const redrawCharts = async () => {
            if (isDesktop.value && !hourlyBirdActivityError.value) {
                await createHourlyChart(hourlyActivityChart, hourlyBirdActivityData.value, { animate: initialLoad.value });
            }

            const isDataEmpty = detailedBirdActivityData.value.length === 0 ||
                detailedBirdActivityData.value.every(bird => bird.hourlyActivity.every(count => count === 0));

            if (!isDataEmpty) {
                await createTotalObsChart(totalObservationsChart, detailedBirdActivityData.value, { animate: initialLoad.value, title: null });
                if (isDesktop.value) {
                    await createHeatmap(hourlyActivityHeatmap, detailedBirdActivityData.value, { animate: initialLoad.value, title: null });
                }
            }

            if (initialLoad.value) initialLoad.value = false;
        };

        const openLatestWithAudio = () => {
            if (latestObservationData.value) {
                showSpectrogram(latestObservationData.value)
            }
        };

        const togglePlayBirdCall = (observation) => {
            if (!observation?.id) return
            const audioUrl = getAudioUrl(observation?.audio_path)
            if (!audioUrl) return
            audioTogglePlay(observation.id, audioUrl)
        };

        const showSpectrogram = (observation) => {
            currentSpectrogramUrl.value = getSpectrogramUrl(observation.file_path)
            currentAudioUrl.value = getAudioUrl(observation.audio_path)
            isSpectrogramModalVisible.value = true
        }

        const formatTimestamp = (dateString) => {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        const formatConfidence = (confidence) => {
             if (confidence === undefined || confidence === null) return '';
            return `${Math.round(confidence * 100)}%`;
        }

        const isDataEmpty = computed(() =>
            !detailedBirdActivityData.value || 
            detailedBirdActivityData.value.length === 0 ||
            detailedBirdActivityData.value.every(bird => bird.hourlyActivity.every(count => count === 0))
        )

        return {
            hourlyBirdActivityData,
            detailedBirdActivityData,
            latestObservationData,
            recentObservationsData,
            summaryData,
            latestObservationimageUrl,
            
            hourlyBirdActivityError,
            detailedBirdActivityError,
            latestObservationError,
            recentObservationsError,
            summaryError,
            
            formatTimestamp,
            formatConfidence,
            
            hourlyActivityChart,
            totalObservationsChart,
            hourlyActivityHeatmap,
            
            isSpectrogramModalVisible,
            currentSpectrogramUrl,
            currentAudioUrl,
            showSpectrogram,

            openLatestWithAudio,

            togglePlayBirdCall,
            currentPlayingId,

            isDesktop,
            isDataEmpty
        }
    }
}
</script>

<style scoped>
/* Scoped styles mainly for specific overrides if Tailwind doesn't cover everything */
.dashboard {
    max-width: 1400px;
}
</style>
