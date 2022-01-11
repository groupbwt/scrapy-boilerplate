import { addExtra, PuppeteerExtra, PuppeteerExtraPlugin } from 'puppeteer-extra';
import puppeteer from 'puppeteer-extra';
import { Browser, Page } from "puppeteer";
import { Logger as LoggerMaker } from "../utils/logger";
import Settings from '../settings';
import { Logger as LoggerInterface } from "winston";


// TODO: add .d.ts file or ignore this syntax
const ProxyPlugin = require('puppeteer-extra-plugin-proxy');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const RecaptchaPlugin = require('puppeteer-extra-plugin-recaptcha');

export default class PuppeteerBrowserMaker {
    private static logger: LoggerInterface;

    public static async getContext(): Promise<{ browser: Browser, page: Page }> {
        if (!this.logger) {
            this.logger = LoggerMaker.createLogger(PuppeteerBrowserMaker.name);
        }

        const settings = Settings.getInstance();

        const puppeteerInstance: PuppeteerExtra = addExtra(puppeteer);

        const plugins: PuppeteerExtraPlugin[] = [
            this.getProxyPlugin(settings),
            this.getRecaptchaPlugin(settings),
            StealthPlugin()
        ].filter((plugin): plugin is PuppeteerExtraPlugin => plugin !== null);

        plugins.forEach((plugin: PuppeteerExtraPlugin) => puppeteerInstance.use(plugin));

        if (!settings.browserOptions.args) {
            settings.browserOptions.args = [];
        }

        settings.browserOptions.args.push('--disable-web-security');
        settings.browserOptions.args.push('--disable-features=IsolateOrigins,site-per-process,UserAgentClientHint');

        if (!(process.platform === "win32")) {
            this.logger.warn('DISABLE SANDBOX');
            settings.browserOptions.args.push('--disable-setuid-sandbox');
            settings.browserOptions.args.push('--no-sandbox');
        }

        const browser = await puppeteerInstance.launch(settings.browserOptions);
        const page = await browser.newPage();

        page.setDefaultNavigationTimeout(settings.navigationTimeout);
        if (!!settings.browserOptions.devtools) {
            // or first request failed
            await page.waitForTimeout(2500);
        }
        return { browser, page };
    }

    private static getProxyPlugin(settings: Settings): PuppeteerExtraPlugin | null {
        if (settings.proxyEnabled) {
            if (settings.proxy.host.length && settings.proxy.port.length) {
                return ProxyPlugin({
                    address: settings.proxy.host,
                    port: Number.parseInt(settings.proxy.port),
                    credentials: {
                        username: settings.proxy.username,
                        password: settings.proxy.password
                    }
                });
            } else {
                throw new Error('Proxy enabled but not configured');
            }
        } else {
            PuppeteerBrowserMaker.logger.warn('PROXY DISABLED');
        }
        return null;
    }

    private static getRecaptchaPlugin(settings: Settings): PuppeteerExtraPlugin | null {
        if (settings.captchaSolverEnabled) {
            if (settings.captchaSolverApiKey) {
                return RecaptchaPlugin({
                    provider: {
                        id: '2captcha',
                        token: settings.captchaSolverApiKey
                    },
                    visualFeedback: true
                });
            } else {
                throw new Error('Captcha solver by API enabled but not configured');
            }
        }
        return null;
    }
}
