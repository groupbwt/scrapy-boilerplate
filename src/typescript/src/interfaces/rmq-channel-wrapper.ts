import { Channel } from 'amqplib-as-promised';

export interface RmqChannelWrapper {
    queueName: string,
    channel: Channel,
    ownerObjectId: string,
}
