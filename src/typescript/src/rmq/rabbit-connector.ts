import amqplib, { Channel, Connection, Message, Options } from 'amqplib';
import { Logger as LoggerInterface } from "winston";
import { Logger } from "../utils/logger";
import { v4 as uuid4 } from 'uuid';
import { RmqChannelWrapper } from "../interfaces/rmq-channel-wrapper";
import { RabbitSettings } from "../interfaces/rabbit-settings";

export class RabbitConnector {
    private readonly host: string;
    private readonly port: string | number;
    private readonly username: string;
    private readonly password: string;
    private readonly vhost: string;
    private readonly logger: LoggerInterface = Logger.createLogger(RabbitConnector.constructor.name);
    private readonly objectId: string;

    private static connection: Connection | null = null;
    private static channels: RmqChannelWrapper[] = [];

    public constructor(
        private rabbitSettings: RabbitSettings
    ) {
        this.host = rabbitSettings.host;
        this.port = rabbitSettings.port;
        this.username = rabbitSettings.username;
        this.password = rabbitSettings.password;
        this.vhost = rabbitSettings.vhost;
        this.objectId = uuid4();
    }

    public static async close() {
        if (RabbitConnector.connection !== null) {
            await RabbitConnector.connection.close();
            RabbitConnector.connection = null;
        }
    }

    public async publish(queueName: string, text: string, options?: Options.Publish) {
        const channel = await this.getChannel(queueName);
        await channel.sendToQueue(queueName, Buffer.from(text), options);
        this.logger.debug(`published message to "${queueName}" queue`);
    }

    public async consume(queueName: string, callback: (channel: Channel, message: Message) => any): Promise<void> {
        const channel = await this.getChannel(queueName);
        const wrapper = async (msg: Message): Promise<any> => {
            await callback(channel, msg!);
        };
        let loggerCounter = 0;
        let loggerStartConsume = Math.floor(Date.now() / 1000);
        let loggerSecond = loggerStartConsume;

        try {
            while (true) {
                const receivedMessage = await channel.get(
                    queueName,
                    { noAck: false }
                );

                if (!!receivedMessage) {
                    await this.logger.debug(`received message with delivery tag ${receivedMessage.fields.deliveryTag}`);
                    await wrapper(receivedMessage);
                    loggerCounter = 0;
                    loggerStartConsume = loggerSecond;
                } else {
                    if (loggerCounter % 30 === 0) {
                        await this.logger.debug(`no messages for more than ${loggerSecond - loggerStartConsume} seconds`);
                        loggerCounter = 1;
                    } else {
                        loggerCounter++;
                        loggerSecond = Math.floor(Date.now() / 1000);
                    }

                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
            }
        } finally {
            await this.close();
        }
    }

    public async close(forceClose: boolean = false) {
        if (RabbitConnector.connection !== null) {
            const channels: RmqChannelWrapper[] = RabbitConnector.channels.filter(
                (ch: RmqChannelWrapper) => ch.ownerObjectId === this.objectId
            );

            for (const channelObject of channels) {
                await channelObject.channel.close();
                this.logger.debug(`closed channel for ${channelObject.queueName} queue`);
            }

            if (RabbitConnector.channels.length === 0 || forceClose) {
                await RabbitConnector.connection.close();
                this.logger.debug(`closed connection on ${this.host}`);
                RabbitConnector.connection = null;
            }
        }
    }

    private async connect(): Promise<void> {
        if (!RabbitConnector.connection) {
            RabbitConnector.connection = await amqplib.connect(this.getConnectionURI());
            this.logger.debug(`opened connection on ${this.host}`);
        }
    }

    private async getChannel(queueName: string): Promise<Channel> {
        const channelItem = RabbitConnector.channels.find((channel) => channel.queueName === queueName);
        let channel: Channel | null = !!channelItem ? channelItem.channel : null;
        if (!channel) {
            await this.connect();
            channel = await RabbitConnector.connection!.createChannel();
            this.logger.debug(`opened channel for "${queueName}" queue`);
            await channel.prefetch(1);
            await channel.assertQueue(queueName, { durable: true });
            RabbitConnector.channels.push({ queueName, channel, ownerObjectId: this.objectId });
        }
        return channel;
    }

    private getConnectionURI(): string {
        return `amqp://${this.username}:${this.password}@${this.host}:${this.port}/${encodeURIComponent(this.vhost)}`;
    }
}
