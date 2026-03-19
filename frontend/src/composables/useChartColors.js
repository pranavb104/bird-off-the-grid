/**
 * Centralized color palette for bird activity charts.
 * Monochrome palette matching the dithered UI theme.
 */
export function useChartColors() {
    const colorPalette = {
        primary: '#0a0a0a',
        secondary: 'rgba(10, 10, 10, 0.55)',
        accent1: 'rgba(10, 10, 10, 0.25)',
        accent2: 'rgba(10, 10, 10, 0.15)',
        text: '#0a0a0a',
        background: '#f0ece3',
        grid: 'rgba(10, 10, 10, 0.12)'
    }

    // RGB values for secondary color (used in heatmap alpha calculations)
    const secondaryRGB = [10, 10, 10]

    return { colorPalette, secondaryRGB }
}
