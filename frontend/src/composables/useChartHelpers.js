import Chart from 'chart.js/auto'

/**
 * Utility functions for Chart.js chart management and data transformation.
 */
export function useChartHelpers() {
    /**
     * Safely destroy a chart if it exists on the given canvas.
     * Uses Chart.js best practice of Chart.getChart() to find existing instances.
     * @param {Ref|HTMLCanvasElement} canvasRef - Vue ref to canvas element or canvas element directly
     */
    const destroyChart = (canvasRef) => {
        // Handle both Vue refs and raw canvas elements
        const isRef = canvasRef && typeof canvasRef === 'object' && 'value' in canvasRef
        const canvas = isRef ? canvasRef.value : canvasRef
        if (!canvas) return

        const existingChart = Chart.getChart(canvas)
        if (existingChart) {
            existingChart.destroy()
        }
    }

    /**
     * Generate array of hour labels for 24-hour display.
     * @returns {string[]} Array of hour strings ['00:00', '01:00', ..., '23:00']
     */
    const generateHourLabels = () => {
        return Array.from({ length: 24 }, (_, i) =>
            i.toString().padStart(2, '0') + ':00'
        )
    }

    /**
     * Calculate min/max statistics for each row of hourly activity data.
     * Used for heatmap color normalization per species.
     * @param {Array<{hourlyActivity: number[]}>} data - Bird activity data
     * @returns {Array<{min: number, max: number}>} Row statistics
     */
    const calculateRowStats = (data) => {
        return data.map(d => ({
            min: Math.min(...d.hourlyActivity),
            max: Math.max(...d.hourlyActivity)
        }))
    }

    /**
     * Transform bird activity data into matrix chart format.
     * Creates a flat array of data points with x (hour), y (species), v (value), and rowStats.
     * @param {Array<{species: string, hourlyActivity: number[]}>} data - Bird activity data
     * @param {Array<{min: number, max: number}>} rowStats - Pre-calculated row statistics
     * @returns {Array<{x: string, y: string, v: number, rowStats: object}>} Matrix data points
     */
    const prepareDataForCategoryMatrix = (data, rowStats) => {
        const hours = generateHourLabels()
        return data.flatMap((d, index) =>
            d.hourlyActivity.map((value, hourIndex) => ({
                x: hours[hourIndex],
                y: d.species,
                v: value,
                rowStats: rowStats[index]
            }))
        )
    }

    return {
        destroyChart,
        generateHourLabels,
        calculateRowStats,
        prepareDataForCategoryMatrix
    }
}
