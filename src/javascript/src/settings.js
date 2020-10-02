/**
 * Settings file for JS scrapers
 */
import * as dotenv from 'dotenv'
import { strtobool } from './utils'


dotenv.config()

export default {
  /**
   * Puppeteer specific settings
   */
  puppeteer: {
    headless: strtobool(process.env.HEADLESS),
    noSandbox: true
  },

  /**
   * RabbitMQ settings
   */
  rabbitmq: {
    username: process.env.RABBITMQ_USERNAME,
    password: process.env.RABBITMQ_PASSWORD,
    host: process.env.RABBITMQ_HOST,
    port: process.env.RABBITMQ_PORT,
    virtualHost: process.env.RABBITMQ_VIRTUAL_HOST,
  },

  /**
   * Sentry error monitoring settings
   */
  sentry: {
    enabled: strtobool(process.env.SENTRY_ENABLED),
    dsn: process.env.SENTRY_DSN,
    release: process.env.SENTRY_RELEASE,
  },
}
