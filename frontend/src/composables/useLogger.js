// Log levels
const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    NONE: 4
}

// Get current log level (default to INFO in production)
const getCurrentLogLevel = () => {
    return import.meta.env?.DEV ? LOG_LEVELS.DEBUG : LOG_LEVELS.INFO
}

const currentLogLevel = getCurrentLogLevel()

// Styled console output
const styles = {
    debug: 'color: #6B7280; font-weight: normal',
    info: 'color: #3B82F6; font-weight: normal',
    warn: 'color: #F59E0B; font-weight: bold',
    error: 'color: #EF4444; font-weight: bold',
    timestamp: 'color: #9CA3AF; font-size: 0.9em',
    component: 'color: #8B5CF6; font-weight: bold'
}

// Format timestamp
const getTimestamp = () => {
    const now = new Date()
    return now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
    })
}

// Create logger instance
export function useLogger(componentName) {
    const logWithLevel = (level, levelName, style, message, ...args) => {
        if (level < currentLogLevel) return

        const timestamp = getTimestamp()
        const prefix = `%c[${timestamp}] %c[${componentName}] %c${levelName}`

        const method = level === LOG_LEVELS.ERROR ? 'error' :
            level === LOG_LEVELS.WARN ? 'warn' :
                'log'

        console[method](
            prefix,
            styles.timestamp,
            styles.component,
            style,
            message,
            ...args
        )
    }

    return {
        debug: (message, ...args) => {
            logWithLevel(LOG_LEVELS.DEBUG, 'DEBUG', styles.debug, message, ...args)
        },

        info: (message, ...args) => {
            logWithLevel(LOG_LEVELS.INFO, 'INFO', styles.info, message, ...args)
        },

        warn: (message, ...args) => {
            logWithLevel(LOG_LEVELS.WARN, 'WARN', styles.warn, message, ...args)
        },

        error: (message, ...args) => {
            logWithLevel(LOG_LEVELS.ERROR, 'ERROR', styles.error, message, ...args)
        },

        // Special method for API calls
        api: (method, url, data = null, response = null) => {
            // Simplified API logging
            logWithLevel(LOG_LEVELS.DEBUG, 'API', styles.info, `${method} ${url}`, { data, response })
        }
    }
}
