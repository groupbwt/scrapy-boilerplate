import Apify from "apify"
import { LaunchPuppeteerOptions } from "apify"
import vanillaPuppeteer from "puppeteer"
import { addExtra } from "puppeteer-extra"
import PuppeteerExtraPluginBlockResources from "puppeteer-extra-plugin-block-resources"
import PuppeteerExtraPluginClickAndWait from "puppeteer-extra-plugin-click-and-wait"
import PuppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth"

import { logger } from '../logging'
import { minToMsec } from '../utils/time'
import RuCaptchaClient from "../utils/RuCaptchaClient"


export default class PuppeteerSpider {
  /**
   * Returns spiger name.
   */
  static get name () { return 'puppeteer_spider' }

  /**
   * Returns viewport settings for page. Use `settings` param to override the defaults.
   *
   * @param {object} settings
   * @returns {object}
   */
  viewport_settings (settings) {
    return Object.assign({
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      isMobile: false,
      hasTouch: false,
      isLandscape: false
    }, settings)
  }

  /**
   * Returns default navigation timeout in milliseconds.
   *
   * @returns {number}
   */
  static get default_navigation_timeout () {
    return minToMsec(5)
  }

  constructor(
    settings,
    ruCaptchaKey = null,
    proxySettings = null
  ) {
    this.settings = settings
    this.start_url = 'https://example.org'
    this._page = undefined
    this._isInitCompleted = false;
    this._ruCaptchaClient = new RuCaptchaClient(ruCaptchaKey);
    this._proxy = proxySettings;
  }

  async __launchBrowser() {
    /**
     * configure Puppeteer Extra browser and plugins
     */
    const puppeteerInstance = addExtra(vanillaPuppeteer);
    puppeteerInstance
      .use(
        PuppeteerExtraPluginStealth()
      )
      .use(
        PuppeteerExtraPluginClickAndWait()
      )
      .use(
        PuppeteerExtraPluginBlockResources({
          blockedTypes: new Set([
            'eventsource',
            'fetch',
            'font',
            'image',
            'manifest',
            'media',
            'other',
            'texttrack',
            'websocket',
            // 'document',
            // 'stylesheet',
            // 'script',
            // 'xhr',
          ])
        })
      )
    ;
    const puppeteerArgs = [];
    let withProxy = this._proxy?.host && this._proxy?.port;
    if (withProxy) {
      puppeteerArgs.push(`--proxy-server=${this._proxy.host}:${this._proxy.port}`);
    }
    /**
     * @type {LaunchPuppeteerOptions}
     */
    const opt = {
      puppeteerModule: puppeteerInstance,
      headless: this.settings.puppeteer.headless,
      args: puppeteerArgs
    };
    this._browser = await Apify.launchPuppeteer(opt);
    this._page = await this._browser.newPage();

    await this._page.setViewport(PuppeteerSpider.VIEWPORT_SETTINGS)
    this.page.setDefaultNavigationTimeout(PuppeteerSpider.default_navigation_timeout)

    if (withProxy && this._proxy?.username && this._proxy?.password) {
      await this._page.authenticate(
        {
          username: this._proxy.username,
          password: this._proxy.password,
        },
      );
    }

    this._isInitCompleted = true;
  };

  async run() {
    while (!this._isInitCompleted) {
      await this.__launchBrowser();
    }
  };

  /**
   * Navigates to a given url making multiple attempts.
   *
   * @param {string} url
   * @param {number} retries
   * @returns {Promise<void>}
   */
  async goWithRetries(url, maxRetries = 3, waitUntil = 'networkidle2') {
    if (this._isInitCompleted) {
      let pageLoadTries = 0;
      let lastError = null;
      while (pageLoadTries < maxRetries) {
        try {
          await this._page.goto(url, {waitUntil: waitUntil});
          let currentURL = this._page.url();
          return
        } catch (e) {
          pageLoadTries += 1;
          lastError = e;
        }
      }
      throw lastError;
    }
    return 0;
  }

  async close() {
    await this._page.close();
    await this._browser.close();
  }
}
