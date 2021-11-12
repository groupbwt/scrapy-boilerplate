import Spider from "../../core/spiders/spider";
import ProcessArguments from "../../interfaces/argv";

import ErrorItem from "../../items/output-item/error-item";
import ExampleInputItem from "../../items/input-item/example-input-item";
import ExampleOutputItem from "../../items/output-item/example-output-item";
import gotoWithRetries from "../../utils/puppeteer/goto-with-retries";
import RecaptchaAudioSolver from "../../utils/puppeteer/recaptcha-audio-solver";
import path from "path";
import { Request } from "puppeteer";

export default abstract class BaseRecaptchaAudioSolverSpider extends Spider {
    private readonly recaptchaWebAudioSolver: RecaptchaAudioSolver;

    protected blockedRequestList: Array<(request: Request) => boolean> = [
        (request) => ["image"].includes(request.resourceType()),
        (request) => request.url().includes('google.com/recaptcha/') && ["image"].includes(request.resourceType())
    ];

    constructor() {
        super();
        this.recaptchaWebAudioSolver = new RecaptchaAudioSolver(
            this.settings.WIT_AI_ACCESS_KEY,
            path.join(process.cwd(), 'storage', 'audio')
        );
    }

    convertArgsToInputMessage(args: ProcessArguments | ExampleInputItem): ExampleInputItem {
        return new ExampleInputItem(args.url);
    }

    async* process(inputMessage: ExampleInputItem): AsyncIterableIterator<ExampleOutputItem | ErrorItem> {
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
                        e.toString(),
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

    async* parsePageWithCaptcha(inputMessage: ExampleInputItem): AsyncIterableIterator<ExampleOutputItem | ErrorItem> {
        await gotoWithRetries(this.page!, inputMessage.url, {
            waitUntil: ['load', "domcontentloaded", "networkidle0"],
            timeout: 60000
        });

        if (inputMessage.url.includes('e-beszamolo.im')) {
            const companyNameInput = await this.page!.waitForSelector('#firmName', { visible: true });
            await companyNameInput.type('food');
            await this.recaptchaWebAudioSolver.recaptchaWebAudioSolver(this.page!);
            const searchButton = await this.page!.waitForSelector('#btnSubmit:not([disabled])', { visible: true });
            await searchButton.click();
        } else if (inputMessage.url.includes('e-cegjegyzek.hu')) {
            const findInput = await this.page!.waitForSelector('#kereses_cegnev', { visible: true });
            await findInput.type(Math.random().toString(36).substr(0, 5), { delay: 150 });
            const submitButton = await this.page!.waitForSelector('#keresesbtn', { visible: true });
            await submitButton.click();
            await this.recaptchaWebAudioSolver.recaptchaWebAudioSolver(this.page!);
            const confirmButton = await this.page!.waitForSelector('#popupOk', { visible: true });
            await confirmButton.click();
        } else {
            await this.recaptchaWebAudioSolver.recaptchaWebAudioSolver(this.page!);
        }
    }
}
