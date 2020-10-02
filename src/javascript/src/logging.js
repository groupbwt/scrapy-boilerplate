/**
 * Logging utilities for headless spiders
 */

import path from 'path'

import { format, transports, createLogger } from 'winston'

const scrapyLogFormat = format.printf(({ level, message, label, timestamp }) => {
  return `${timestamp} [${label}] ${level.toUpperCase()}: ${message}`
})

export const logger = createLogger()

const defaultLoggingOptions = {
  level: 'debug',
  label: 'pptr',
  logFile: null
}

export function loggingConfig (options) {
  options = Object.assign({}, defaultLoggingOptions, options)

  const logTransports = [
    new transports.Console({
      stderrLevels: ['debug', 'info', 'warn', 'error', 'critical']
    })
  ]

  if (options.logFile) {
    logTransports.push(new transports.File({
      filename: path.join('..', 'logs', options.logFile),
      options: { flags: 'a' }
    }))
  }

  logger.configure({
    level: options.level,
    format: format.combine(
      format.splat(),
      format.label({ label: options.label }),
      format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
      scrapyLogFormat
    ),
    transports: logTransports
  })
}

loggingConfig({
  level: 'debug',
  label: 'headless'
})
