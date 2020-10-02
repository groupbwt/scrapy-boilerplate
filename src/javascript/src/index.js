/**
 * Entry point for JS-based headless browser scrapers
 * Implemented with Puppeteer (https://pptr.dev)
 * For usage instructions run: node build/index.js help
 *
 * jshint esversion: 8
 */
import * as Sentry from '@sentry/node'
import * as yargs from 'yargs'

import { logger, loggingConfig } from './logging'
import settings from './settings'
import * as spiders from './spiders'
import PuppeteerSpider from './spiders/PuppeteerSpider'


/**
 * Inits Sentry.io monitoring.
 */
function initSentry () {
  const sentryDSN = settings.sentry.dsn
  if (sentryDSN) {
    Sentry.init({
      dsn: sentryDSN
    })
  }
}

/**
 * Global catch-all callback for rejected promises.
 *
 * @param {String} reason
 * @param {Promise} p
 */
function handleRejection (reason, p) {
  logger.error('Unhandled promise rejection: %s', reason)
  process.exit(1)
}

/**
 * Global catch-all callback for unhandled exceptions.
 *
 * @param {Error} err
 */
function handleException (err) {
  logger.error(err)
  logger.debug(err.stack)
  process.exit(1)
}

/**
 * Gets available spiders.
 *
 * @returns {Map<String, Object>}
 */
function getSpiders () {
  const available = Object.entries(spiders).reduce((result, [_, obj]) => {
    console.log(obj)
    if (obj.prototype instanceof PuppeteerSpider && 'name' in obj) {
      return result.concat(obj)
    }
    return result
  }, [])

  const spidersByName = new Map()

  for (const spider of available) {
    spidersByName.set(spider.name, spider)
  }

  return spidersByName
}

/**
 * Lists available spiders.
 */
function listSpiders () {
  for (const name of getSpiders().keys()) {
    process.stdout.write(`${name}\n`)
  }
}

/**
 * Runs a scraper by its name priovided in argv.
 *
 * @param {Object} argv
 * @returns {Promise<void>}
 */
async function runSpider (argv) {
  const availableSpiders = getSpiders()
  if (availableSpiders.has(argv.spider)) {
    const spiderCls = availableSpiders.get(argv.spider)
    const spider = new spiderCls(settings)

    // configure logging
    loggingConfig({
      logFile: `${argv.spider}.log`,
      label: argv.spider
    })

    try {
      await spider.run(settings)
    } catch (err) {
      logger.error('Error running spider %s', argv.spider)
      logger.debug(err.stack)
      await spider.close()
      process.exit(1)
    }
  } else {
    logger.error('Unknown spider: %s', argv.spider)
    process.exit(1)
  }
}

// main
process.on('uncaughtException', handleException)
process.on('unhandledRejection', handleRejection)

initSentry()

const argv = yargs
  .command('list', 'List available scrapers', () => {}, argv => {
    listSpiders()
  })
  .command('crawl <spider>', 'Run a scraper by name', () => {}, argv => {
    runSpider(argv)
  })
  .help()
  .argv
