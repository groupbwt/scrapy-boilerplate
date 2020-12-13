import Spider from "../core/spiders/spider";
import RmqPipeline from "../pipelines/rmq-pipeline";
import Argv from "../core/interfaces/argv";
import InputItem from "../items/input-item/input-item";
import { Response } from "puppeteer";
import OutputItem from "../items/output-item/item";
import gotoWithRetries from "../utils/puppeteer/goto-with-retries";
import ErrorItem from "../items/output-item/error-item";
import TestSpiderProperties from "../core/interfaces/test-spider-properties";


export default class TestSpider extends Spider {
    public static spiderName: string = 'test_spider';
    public taskQueueName = this.settings.TEST_SPIDER_TASK_QUEUE;

    getCustomSettingsProperties(): TestSpiderProperties {
        return {
            pipelines: [
                RmqPipeline,
            ],
        };
    }

    convertArgsToInputMessage(argv: Argv): InputItem {
        return {
            id: argv.id,
            url: argv.url,
        };
    }

    async* process(inputMessage: InputItem): AsyncIterableIterator<OutputItem> {
        let error = null;
        let response: Response | null = null;
        //@ts-ignore
        let url = inputMessage.url;

        for (let attempt = 0; attempt < 5; attempt++) {
            try {
                response = await gotoWithRetries(this.page!, url, { waitUntil: ["networkidle0", "load", "domcontentloaded"] });
                if (!!response) {
                    this.logger.debug(`Crawled ${response.url()} (${response.status()})`);
                } else {
                    this.logger.debug(`Crawled ${url} (null)`);
                }

                if (!!response && response.url().includes('google.com')) {
                    throw new Error(`captcha received (attempt ${attempt})`);
                }

                // extractData
                this.logger.info(`Parsed ${url}`);
                return;
            } catch (e) {
                this.logger.warn(e);
                error = e;
                await this.restartBrowser();
            }
        }

        if (error) {
            this.logger.error(error);
            yield new ErrorItem(
                error.toString(),
                null, // error.stack ? error.stack: null,
                response !== null ? response.url() : url,
                !!response ? response.status() : null,
                null,
                inputMessage,
            );
        }
    }
}
