import { ref } from "vue";
import api from "@/services/api";
import { useLogger } from "./useLogger";

export function useFetchBirdData() {
    const logger = useLogger('useFetchBirdData');

    const detailedBirdActivityData = ref([]);
    const hourlyBirdActivityData = ref([]);
    const latestObservationData = ref((null));
    const recentObservationsData = ref([]);
    const summaryData = ref({});
    const latestObservationimageUrl = ref("/default_bird.webp");

    const detailedBirdActivityError = ref(null);
    const hourlyBirdActivityError = ref(null);
    const latestObservationError = ref(null);
    const recentObservationsError = ref(null);
    const summaryError = ref(null);


    // Transform raw detection rows → [{ species, hourlyActivity: [24 counts] }]
    const transformToHourlyActivity = (detections) => {
        const map = {};
        for (const det of detections) {
            const species = det.common_name || det.scientific_name;
            if (!map[species]) {
                map[species] = { species, hourlyActivity: new Array(24).fill(0) };
            }
            const hour = parseInt((det.time || '').split(':')[0], 10);
            if (hour >= 0 && hour < 24) {
                map[species].hourlyActivity[hour]++;
            }
        }
        return Object.values(map);
    };

    const fetchChartsData = async (date) => {
        logger.info('Fetching charts data', { date });
        try {
            const [hourlyBirdActivityResponse, detailedBirdActivityResponse] =
                await Promise.all([
                    api.get('/hourly', { params: { date } })
                        .catch(error => ({ error })),
                    api.get('/detections', { params: { date, limit: 1000 } })
                        .catch(error => ({ error }))
                ]);

            if (hourlyBirdActivityResponse.error) {
                hourlyBirdActivityError.value = "Failed to fetch hourly activity data.";
                hourlyBirdActivityData.value = [];
            } else {
                hourlyBirdActivityData.value = hourlyBirdActivityResponse.data;
                hourlyBirdActivityError.value = null;
            }

            if (detailedBirdActivityResponse.error) {
                detailedBirdActivityError.value = "Failed to fetch detailed activity data.";
                detailedBirdActivityData.value = [];
            } else {
                detailedBirdActivityData.value = transformToHourlyActivity(detailedBirdActivityResponse.data);
                detailedBirdActivityError.value = null;
            }

        } catch (error) {
            logger.error('Error fetching charts data', error);
        }
    };


    const fetchDashboardData = async () => {
        logger.info('Fetching dashboard data');
        try {
            const today = new Date().toLocaleDateString("en-CA");
            fetchChartsData(today);

            const [latestObsResp, recentObsResp, summaryResp] = await Promise.all([
                api.get('/recent', { params: { limit: 1 } }).catch(error => ({ error })),
                api.get('/recent').catch(error => ({ error })),
                api.get('/overview').catch(error => ({ error }))
            ]);

            if (latestObsResp.error) {
                latestObservationError.value = "Failed to fetch latest observation.";
                latestObservationData.value = null;
            } else {
                latestObservationData.value = latestObsResp.data?.[0] ?? null;
                latestObservationError.value = null;
            }

            if (recentObsResp.error) {
                recentObservationsError.value = "Failed to fetch recent observations.";
                recentObservationsData.value = [];
            } else {
                recentObservationsData.value = recentObsResp.data;
                recentObservationsError.value = null;
            }

            if (summaryResp.error) {
                summaryError.value = "Failed to fetch summary.";
                summaryData.value = {};
            } else {
                summaryData.value = summaryResp.data;
                summaryError.value = null;
            }

            if (latestObservationData.value) {
                try {
                    const species = latestObservationData.value.common_name || latestObservationData.value.scientific_name;
                    const resp = await fetch(
                        `https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json` +
                        `&piprop=thumbnail&pithumbsize=400&titles=${encodeURIComponent(species)}&origin=*`
                    );
                    const json = await resp.json();
                    const pages = json.query?.pages ?? {};
                    const page = Object.values(pages)[0];
                    if (page?.thumbnail?.source) {
                        latestObservationimageUrl.value = page.thumbnail.source;
                    }
                } catch (e) {
                    logger.warn('Failed to fetch wikimedia image', e);
                }
            }

        } catch (error) {
            logger.error('Error fetching dashboard data', error);
        }
    };

    return {
        hourlyBirdActivityData,
        detailedBirdActivityData,
        latestObservationData,
        recentObservationsData,
        summaryData,

        hourlyBirdActivityError,
        detailedBirdActivityError,
        latestObservationError,
        recentObservationsError,
        summaryError,

        latestObservationimageUrl,

        fetchDashboardData,
        fetchChartsData
    };
}
