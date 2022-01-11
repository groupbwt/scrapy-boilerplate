import { Browser, Page, HTTPRequest } from "puppeteer";
import { LoggingLevel, Logger } from "../../utils/logger";
import InputItem from "../../items/input-item/input-item";
import OutputItem from "../../items/output-item/output-item";
import Settings from "../../settings";
import PuppeteerBrowserMaker from "../puppeteer-browser-maker";
import SettingsProperties from "../../interfaces/settings-properties";
import ProcessArguments from "../../interfaces/argv";


export default abstract class Spider {
    public static spiderName: string = 'base';

    abstract taskQueueName: string;
    public settings: Settings;
    public logger = Logger.createLogger(this.constructor.name);
    protected blockedRequestList: Array<(request: HTTPRequest) => boolean> = [];
    protected allowedRequestList: Array<(request: HTTPRequest) => boolean> = [];
    protected browser: Browser | null = null;
    protected page: Page | null = null;

    constructor() {
        this.settings = Settings.getInstance(this.getCustomSettingsProperties());
    }

    abstract getCustomSettingsProperties(): SettingsProperties;

    abstract convertArgsToInputMessage(args: ProcessArguments | object): InputItem;


    abstract process(inputMessage: InputItem): AsyncIterableIterator<OutputItem>;

    public async* run(args: ProcessArguments): AsyncIterableIterator<OutputItem> {
        for await (const item of this.process(this.convertArgsToInputMessage(args))) {
            yield item;
        }
    };

    public async* consume(args: object): AsyncIterableIterator<OutputItem> {
        for await (const item of this.process(this.convertArgsToInputMessage(args))) {
            yield item;
        }
    }

    protected async addRequestFilter(page: Page) {
        await page.setRequestInterception(true);
        page.on('request', async (request: HTTPRequest) => {
                if (this.allowedRequestList.some(func => func(request))) {
                    await request.continue();
                    return;
                }

                if (this.blockedRequestList.some(func => func(request))) {
                    await request.abort();
                    return;
                }

                await request.continue();
            }
        );
    }

    public async spiderOpened(): Promise<void> {
        const { browser, page } = await PuppeteerBrowserMaker.getContext();
        await this.addRequestFilter(page);
        this.browser = browser;
        this.page = page;
    }

    public async spiderClosed() {
        await this.closeBrowser();
    }

    public async restartBrowser(): Promise<void> {
        await this.closeBrowser();
        const context = await PuppeteerBrowserMaker.getContext();
        await this.addRequestFilter(context.page);
        this.browser = context.browser;
        this.page = context.page;
        this.logger.debug('browser restarted successfully');
    }

    private async closeBrowser() {
        if (this.browser) {
            try {
                await this.browser.close();
            } catch (e) {
                this.logger.warning(`close browser - ${e}`);
                for (let page of await this.browser.pages()) {
                    await page.close();
                }
                await this.browser.close();
            }
            this.browser = null;
        }
    }
}
