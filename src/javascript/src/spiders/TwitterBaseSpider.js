import Apify from "apify";
import {LaunchPuppeteerOptions} from "apify";
import vanillaPuppeteer from "puppeteer";
import {addExtra} from "puppeteer-extra";
import PuppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth";
import PuppeteerExtraPluginClickAndWait from "puppeteer-extra-plugin-click-and-wait";
import PuppeteerExtraPluginBlockResources from "puppeteer-extra-plugin-block-resources";
import RuCaptchaClient from "../utils/RuCaptchaClient";
import pauseFor from "../utils/pause";

const {puppeteer} = Apify.utils;


class TwitterBaseSpider {
  static get VIEWPORT_SETTINGS() {
    return {
      width: 1920,
      // height: 6480,
      height: 1080,
      deviceScaleFactor: 1,
      isMobile: false,
      hasTouch: false,
      isLandscape: false,
    };
  }

  constructor(headless = false, ruCaptchaKey = null, proxySettings = null) {
    this._isInitCompleted = false;
    this._headless = headless;
    this._ruCaptchaClient = new RuCaptchaClient(ruCaptchaKey);
    this._proxy = proxySettings;
  };

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
            // 'document',
            // 'stylesheet',
            'image',
            'media',
            'font',
            // 'script',
            'texttrack',
            // 'xhr',
            'fetch',
            'eventsource',
            'websocket',
            'manifest',
            'other',
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
      headless: this._headless,
      args: puppeteerArgs
    };
    this._browser = await Apify.launchPuppeteer(opt);
    this._page = await this._browser.newPage();

    // await this._page.setViewport(LinkedInRegularSpider.VIEWPORT_SETTINGS);
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

  async goWithRetries(url, maxRetries = 3, waitUntil = 'networkidle2') {
    if (this._isInitCompleted) {
      let pageLoadTries = 0;
      let lastError = null;
      while (pageLoadTries < maxRetries) {
        try {
          await this._page.goto(url, {waitUntil: waitUntil});
          let currentURL = await this._page.url();
          return
        } catch (e) {
          pageLoadTries += 1;
          // console.log('pageLoadTries', pageLoadTries, url);
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

module.exports = TwitterBaseSpider;
