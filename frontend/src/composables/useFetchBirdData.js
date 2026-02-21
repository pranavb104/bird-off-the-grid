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
    const latestObservationimageUrl = ref("/default_bird.webp"); // You might need to add this asset

    const detailedBirdActivityError = ref(null);
    const hourlyBirdActivityError = ref(null);
    const latestObservationError = ref(null);
    const recentObservationsError = ref(null);
    const summaryError = ref(null);


    const fetchChartsData = async (date) => {
        logger.info('Fetching charts data', { date });
        try {
            const [hourlyBirdActivityResponse, detailedBirdActivityResponse] =
                await Promise.all([
                    api.get('/activity/hourly', { params: { date } })
                        .catch(error => ({ error })),
                    api.get('/activity/overview', { params: { date } })
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
                detailedBirdActivityData.value = detailedBirdActivityResponse.data;
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
                api.get('/observations/latest').catch(error => ({ error })),
                api.get('/observations/recent').catch(error => ({ error })),
                api.get('/observations/summary').catch(error => ({ error }))
            ]);

            if (latestObsResp.error) {
                latestObservationError.value = "Failed to fetch latest observation.";
                latestObservationData.value = null;
            } else {
                latestObservationData.value = latestObsResp.data;
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
                // Fetch wikimedia image if available
                try {
                    const wikimediaImageResponse = await api.get('/wikimedia_image', {
                        params: { species: latestObservationData.value.common_name }
                    });
                    if (wikimediaImageResponse.data?.imageUrl) {
                        latestObservationimageUrl.value = wikimediaImageResponse.data.imageUrl;
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
