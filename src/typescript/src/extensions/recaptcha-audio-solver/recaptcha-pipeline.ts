import { Message } from "amqplib";
import RmqPipeline from "../../pipelines/rmq-pipeline";
import RecaptchaOutputItem from "./recaptcha-output-item";
import ErrorItem from "../../items/output-item/error-item";
import RecaptchaSpider from "./recaptcha-spider";
import Argv from "../../interfaces/argv";
import Settings from "../../settings";

export default class RecaptchaPipeline extends RmqPipeline {
    public constructor(
        protected spider: RecaptchaSpider,
        protected argv: Argv,
        protected settings: Settings
    ) {
        super(spider, argv, settings);
    }

    async process(item: RecaptchaOutputItem | ErrorItem, msg?: Message): Promise<RecaptchaOutputItem | ErrorItem | null> {
        if (this.argv.type === "worker") {

            const options = {
                deliveryMode: 2,
                persistent: true,
                contentType: 'application/json',
                correlationId: msg && msg.properties ? msg.properties.correlationId : undefined
            };

            const jsonItem = JSON.stringify(item);
            this.logger.debug(jsonItem);

            if (item instanceof RecaptchaOutputItem || item instanceof ErrorItem) {
                await this.connector!.publish(this.spider.resultQueueName, jsonItem, options);
            } else {
                this.logger.error('unsupported item');
            }
        }

        return item;
    }
}
