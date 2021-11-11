import axios from "axios";
import { Logger } from '../logger';
import { Logger as LoggerInterface } from "winston";
import pauseFor from "../sleep";


export default class RuCaptchaClient {
    logger: LoggerInterface;

    static get RU_CAPTCHA_SEND_ENDPOINT(): string {
        return 'http://rucaptcha.com/in.php';
    }

    static get RU_CAPTCHA_CHECK_RES_ENDPOINT(): string {
        return 'http://rucaptcha.com/res.php';
    }

    static get TICK_PERIOD(): number {
        return 5000;
    }

    static get MAX_TICKS(): number {
        return 60;
    }

    constructor(
        private apiKey: string
    ) {
        this.logger = Logger.createLogger(this.constructor.name);
        // pass
    }

    async getSolution(
        googleSiteKey: string,
        currentUrl: string
        // proxyUser: string,
        // proxyPassword: string,
        // proxyAddress: string,
        // proxyType = 'HTTP'
    ): Promise<string> {
        let captchaToken: string = '';
        let ticks = 0;
        const ruCaptchaSendResponse = await axios.get(RuCaptchaClient.RU_CAPTCHA_SEND_ENDPOINT, {
            params: {
                key: this.apiKey,
                method: 'userrecaptcha',
                googlekey: googleSiteKey,
                pageurl: currentUrl,
                here: 'now',
                json: '1'
                // proxy: `${proxyUser}:${proxyPassword}@${proxyAddress}`,
                // proxytype: proxyType,
            }
        });

        const ruCaptchaRequestId = ruCaptchaSendResponse.data.request;
        if (ruCaptchaRequestId === 'ERROR_ZERO_BALANCE') {
            return Promise.reject(new Error(ruCaptchaRequestId));
        }

        while (!captchaToken && (ticks < RuCaptchaClient.MAX_TICKS)) {
            ticks += 1;
            await pauseFor(RuCaptchaClient.TICK_PERIOD);
            try {
                const ruCaptchaSolutionResponse = await axios.get(RuCaptchaClient.RU_CAPTCHA_CHECK_RES_ENDPOINT, {
                    params: {
                        key: this.apiKey,
                        action: 'get',
                        id: ruCaptchaRequestId,
                        json: '1'
                        // proxy: `${proxyUser}:${proxyPassword}@${proxyAddress}`,
                        // proxytype: proxyType,
                    }
                });
                this.logger.info("tick %s; ruCaptchaSolutionResponse: %s", ruCaptchaSolutionResponse);
                if (parseInt(ruCaptchaSolutionResponse.data.status, 10) === 1) {
                    captchaToken = ruCaptchaSolutionResponse.request;
                }
            } catch (e: unknown) {
                this.logger.warn(e instanceof Error ? e.toString() : e);
            }
        }
        if (captchaToken) {
            return Promise.resolve(captchaToken);
        }
        return Promise.reject(new Error('CAPTCHA_SOLUTION_ERROR'));
    }
}
