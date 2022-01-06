import BasePipeline from "./base-pipeline";
import { RabbitConnector } from "../rmq/rabbit-connector";
import OutputItem from "../items/output-item/output-item";

export default class RmqPipeline extends BasePipeline {
    protected connector: RabbitConnector | undefined;

    async init(): Promise<void> {
        this.connector = new RabbitConnector(this.settings.rabbit);
    }

    async close(): Promise<void> {
        await this.connector!.close();
    }

    async process(item: OutputItem): Promise<OutputItem | null> {
        if (this.argv.type === "worker") {

            const options = {
                deliveryMode: 2,
                persistent: true,
                contentType: 'application/json',
            };

            const jsonItem = JSON.stringify(item);
            this.logger.debug(jsonItem);

            this.logger.error('RmqPipeline is not configured');
            // if (item instanceof YourItem) {
            //     await this.connector!.publish(this.settings.YOUR_RESULT_QUEUE, jsonItem, options);
            // } else {
            //     this.logger.error('unsupported item');
            // }
        }

        return item;
    }
}
