import Spider from "../core/spiders/spider";
import RmqPipeline from "../pipelines/rmq-pipeline";
import { Response } from "puppeteer";
import gotoWithRetries from "../utils/puppeteer/goto-with-retries";
import ProcessArguments from "../interfaces/argv";

import ExampleSpiderProperties from "../interfaces/example-spider-properties";
import ErrorItem from "../items/output-item/error-item";
import ExampleInputItem from "../items/input-item/example-input-item";
import ExampleOutputItem from "../items/output-item/example-output-item";


export default class ExampleSpider extends Spider {
    public static spiderName: string = 'example';
    public taskQueueName = this.settings.EXAMPLE_SPIDER_TASK_QUEUE;

    getCustomSettingsProperties(): ExampleSpiderProperties {
        return {
            pipelines: [
                RmqPipeline,
            ],
        };
    }

    convertArgsToInputMessage(args: ProcessArguments | ExampleInputItem): ExampleInputItem {
        return new ExampleInputItem(args.url);
    }

    async* process(inputMessage: ExampleInputItem): AsyncIterableIterator<ExampleOutputItem | ErrorItem> {
        let error = null;
        let response: Response | null = null;
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
