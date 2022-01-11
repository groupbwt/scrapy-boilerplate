import Spider from "../../core/spiders/spider";
import ProcessArguments from "../../interfaces/argv";

import ErrorItem from "../../items/output-item/error-item";
import RecaptchaInputItem from "./recaptcha-input-item";
import RecaptchaAudioSolver from "./recaptcha-audio-solver";
import path from "path";
import { HTTPRequest, HTTPResponse, Page } from "puppeteer";
import RecaptchaOutputItem from "./recaptcha-output-item";
import crypto from "crypto";
import fs from "fs";
import ExampleSpiderProperties from "../../interfaces/example-spider-properties";
import RecaptchaPipeline from "./recaptcha-pipeline";


export default abstract class RecaptchaSpider extends Spider {
    private readonly recaptchaAudioSolver: RecaptchaAudioSolver;
    private CACHE_DIR: string = path.join(process.cwd(), 'storage', 'cache');

    protected blockedRequestList: Array<(request: HTTPRequest) => boolean> = [
        (request) => ["image"].includes(request.resourceType()),
        (request) => request.url().includes('.woff'),
        (request) => request.url().includes('.ico'),
        (request) => request.url().includes('data:image/png')
    ];

    public sitekey: string = '';

    abstract cacheEnabled: boolean;
    abstract resultQueueName: string;

    constructor() {
        super();
        this.recaptchaAudioSolver = new RecaptchaAudioSolver(
            this.settings.WIT_AI_ACCESS_KEY,
            path.join(process.cwd(), 'storage', 'audio')
        );
    }

    getCustomSettingsProperties(): ExampleSpiderProperties {
        return {
            pipelines: [
                RecaptchaPipeline
            ]
        };
    }

    convertArgsToInputMessage(args: ProcessArguments | RecaptchaInputItem): RecaptchaInputItem {
        return new RecaptchaInputItem(args.url, args.sitekey);
    }

    public async* process(inputMessage: RecaptchaInputItem): AsyncIterableIterator<RecaptchaOutputItem | ErrorItem> {
        this.logger.info(`received url ${inputMessage.url}`);
        const maxRetryTimes = 3;

        for (let attempt = 0; attempt < maxRetryTimes; attempt++) {
            try {
                for await (const item of this.parsePageWithCaptcha(inputMessage)) {
                    yield item;
                }
                break;
            } catch (e) {
                this.logger.warn(e);
                await this.restartBrowser();

                if (attempt === maxRetryTimes - 1) {
                    this.logger.error(e);
                    yield new ErrorItem(
                        e instanceof Error ? e.toString() : String(e),
                        null,
                        inputMessage.url,
                        null,
                        null,
                        inputMessage
                    );
                }
            }
        }
    }

    public async* parsePageWithCaptcha(inputMessage: RecaptchaInputItem): AsyncIterableIterator<RecaptchaOutputItem | ErrorItem> {
        // await this.page!.setExtraHTTPHeaders({
        //     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15',
        // });
        this.setSitekey(inputMessage.sitekey);
        await Promise.all([
            this.page!.goto(inputMessage.url, { waitUntil: ['load', "domcontentloaded", "networkidle0"] }),
            this.page!.waitForResponse((r: HTTPResponse) => r.url().includes('api.js')),
            this.page!.waitForResponse((r: HTTPResponse) => r.url().includes('recaptcha__en.js'))
        ]);

        const gRecaptchaResponse = await this.recaptchaAudioSolver.solve(this.page!);
        yield new RecaptchaOutputItem(gRecaptchaResponse);
    }

    public setSitekey(sitekey: string) {
        this.sitekey = sitekey;
    }

    protected async addRequestFilter(page: Page) {
        await page.setRequestInterception(true);
        page.on('request', async (request: HTTPRequest) => {
            if (request.isNavigationRequest() && request.frame() === this.page!.mainFrame()) {
                return await request.respond({
                    status: 200,
                    headers: { 'local-cache': true },
                    contentType: 'text/html; charset=utf-8',
                    body: `<html>
                    <head>
                    <title>reCAPTCHA</title>
                    <script src="https://www.google.com/recaptcha/api.js" async ></script>
                    </head>
                    <body>
                    <form action="?" method="POST">
                        <div class="g-recaptcha" data-sitekey="${this.sitekey}"></div>
                        <br/>
                        <input type="submit" value="Submit">
                    </form>
                    </body>
                </html>`
                });
            }

            if (this.allowedRequestList.some(func => func(request))) {
                // pass
            } else if (this.blockedRequestList.some(func => func(request))) {
                await request.abort();
                return;
            }

            if (this.cacheEnabled && this.isCached(request)) {
                const rawContent = this.getResponseFromCache(request);
                if (rawContent) {
                    const content = JSON.parse(rawContent);
                    this.logger.debug(`the response was created from a local cache ${request.url()}`);
                    return await request.respond({
                        'status': 200,
                        'headers': { ...content.headers, 'local-cache': 'true' },
                        'body': content.body
                    });
                }
            }

            await request.continue();
        });

        page.on('response', async (r: HTTPResponse) => {
            if (this.cacheEnabled && r.ok()) {
                if (this.isCached(r.request())) {
                    const filePath = this.requestToFilename(r.request());
                    if (!fs.existsSync(filePath)) {
                        fs.writeFileSync(filePath, JSON.stringify({
                            'url': r.request().url(),
                            'body': await r.text(),
                            'headers': r.headers()
                        }));
                    }
                }
            }
        });
    }

    private requestToFilename(request: HTTPRequest): string {
        const resourceType = request.resourceType();
        const urlHash = crypto.createHash('md5').update(request.url()).digest('hex');
        const host = (new URL(request.url())).host;
        return `${this.CACHE_DIR}/${host}-${urlHash}.${resourceType}.json`;
    }

    private getResponseFromCache(request: HTTPRequest): string | void {
        const filePath = this.requestToFilename(request);
        if (!fs.existsSync(filePath)) {
            return;
        }
        try {
            return fs.readFileSync(filePath, 'utf8');
        } catch (err) {
            return;
        }
    }

    private isCached(request: HTTPRequest) {
        return (
            request.url().includes('http') &&
            !request.isNavigationRequest() &&
            (['stylesheet', 'script'].includes(request.resourceType()) || request.url().includes('api2/webworker.js')) &&
            request.method() === 'GET'
        );
    }
}
