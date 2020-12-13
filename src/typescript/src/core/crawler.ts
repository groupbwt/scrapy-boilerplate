import spiders from "../spiders";
import { Logger as LoggerInterface } from "winston";
import { levels, Logger } from "../utils/logger";
import BasePipeline from "../pipelines/base-pipeline";
import { RabbitConnector } from "../rmq/rabbit-connector";
import { Channel, Message } from "amqplib-as-promised/lib";
import Settings from "../settings";
import Spider from "./spiders/spider";
import Argv from "../interfaces/argv";


export default class Crawler {
    protected static logger: LoggerInterface = Logger.createLogger(Crawler.constructor.name, levels.DEBUG);

    public static async run(argv: Argv) {
        const spiderClass = Crawler.getSpider(argv);
        //@ts-ignore TODO
        const spider: Spider = new spiderClass(argv);
        const settings: Settings = Settings.getInstance();

        const pipelines: BasePipeline[] = settings.pipelines.map(<T extends BasePipeline>(PipelineChild: typeof BasePipeline): T => {
            //@ts-ignore TODO
            return new PipelineChild(argv, settings);
        });

        for await (const pipeline of pipelines) {
            await pipeline.init();
        }

        try {
            await spider.spiderOpened();
            if (argv.type === 'parser') {
                for await (const item of spider.run(argv)) {
                    for (const pipeline of pipelines) {
                        await pipeline.process(item);
                    }
                }
            } else if (argv.type === 'worker') {
                if (!spider.taskQueueName) {
                    throw new Error("No task queue name in spider");
                }

                const connector = new RabbitConnector(settings.rabbit);
                this.logger.debug(`start consuming from "${spider.taskQueueName}" queue`);
                await connector.consume(spider.taskQueueName, async (channel: Channel, msg: Message): Promise<any> => {
                    try {
                        const messageJson = JSON.parse(msg.content.toString());
                        for await (const item of spider.consume(messageJson)) {
                            for (const pipeline of pipelines) {
                                await pipeline.process(item);
                            }
                        }
                        if (msg.properties.replyTo) {
                            await connector.publish(
                                msg.properties.replyTo,
                                msg.content.toString(),
                                { deliveryMode: 2, persistent: true, contentType: 'application/json' }
                            );
                            this.logger.debug(`task message reply to ${msg.properties.replyTo} queue`);
                        }
                        channel.ack(msg);
                        this.logger.debug(`ACK message with delivery tag ${msg.fields.deliveryTag}`);
                    } catch (e) {
                        this.logger.error(e);
                        channel.ack(msg);
                        this.logger.debug(`${"*".repeat(35)} ACK message (ERROR) with delivery tag ${msg.fields.deliveryTag} ${"*".repeat(35)}`);
                        const messageJson = JSON.parse(msg.content.toString());
                        this.logger.debug(`${messageJson}`);
                        this.logger.debug(`${"*".repeat(70)}`);
                    }
                });
            } else {
                throw Error('Missing required field argv.type');
            }
            for await (const pipeline of pipelines) {
                await pipeline.close();
            }
        } finally {
            await spider.spiderClosed();
            await (new RabbitConnector(settings.rabbit)).close(true);
        }
    }

    protected static getSpider({ spiderName }: { spiderName: string }): typeof Spider {
        const spider = spiders.find((spider) => spider.spiderName === spiderName);
        if (spider) {
            return spider;
        } else {
            const message = `Spider with name "${spiderName}" not found`;
            Crawler.logger.error(message);
            throw Error(message);
        }
    }
}
