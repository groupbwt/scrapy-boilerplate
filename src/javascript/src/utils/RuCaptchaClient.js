import rp from 'request-promise-native';
import { logger } from '../logging'


export default class RuCaptchaClient {
  static get RU_CAPTCHA_SEND_ENDPOINT() {
    return 'http://rucaptcha.com/in.php';
  }

  static get RU_CAPTCHA_CHECK_RES_ENDPOINT() {
    return 'http://rucaptcha.com/res.php';
  }

  static get TICK_PERIOD() {
    return 5000;
  }

  static get MAX_TICKS() {
    return 60;
  }

  constructor(apiKey) {
    this._apiKey = apiKey;
  }

  async _waitFor(time) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        resolve();
      }, time);
    });
  }

  async getSolution(googleSiteKey, currentUrl, proxyUser, proxyPassword, proxyAddress, proxyType = 'HTTP') {
    let captchaToken = false;
    let ticks = 0;
    const ruCaptchaSendResponse = await rp.get({
      uri: RuCaptchaClient.RU_CAPTCHA_SEND_ENDPOINT,
      json: true,
      qs: {
        key: this._apiKey,
        method: 'userrecaptcha',
        googlekey: googleSiteKey,
        pageurl: currentUrl,
        here: 'now',
        json: '1',
        proxy: `${proxyUser}:${proxyPassword}@${proxyAddress}`,
        proxytype: proxyType,
      },
    });

    const ruCaptchaRequestId = ruCaptchaSendResponse.request;
    if (ruCaptchaRequestId === 'ERROR_ZERO_BALANCE') {
      return Promise.reject(new Error(ruCaptchaRequestId));
    }

    while ((captchaToken === false) && (ticks < RuCaptchaClient.MAX_TICKS)) {
      ticks += 1;
      await this._waitFor(RuCaptchaClient.TICK_PERIOD);
      try {
        const ruCaptchaSolutionResponse = await rp.get({
          uri: RuCaptchaClient.RU_CAPTCHA_CHECK_RES_ENDPOINT,
          json: true,
          qs: {
            key: this._apiKey,
            action: 'get',
            id: ruCaptchaRequestId,
            json: '1',
            proxy: `${proxyUser}:${proxyPassword}@${proxyAddress}`,
            proxytype: proxyType,
          },
        });
        logger.info("tick %s; ruCaptchaSolutionResponse: %s", ruCaptchaSolutionResponse);
        if (parseInt(ruCaptchaSolutionResponse.status, 10) === 1) {
          captchaToken = ruCaptchaSolutionResponse.request;
        }
      } catch (e) {
        logger.warn(e.toString());
      }
    }
    if (captchaToken !== false) {
      return Promise.resolve(captchaToken);
    }
    return Promise.reject(new Error('CAPTCHA_SOLUTION_ERROR'));
  }
}
