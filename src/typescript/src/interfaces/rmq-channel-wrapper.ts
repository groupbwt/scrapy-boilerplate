import { Channel } from 'amqplib';

export interface RmqChannelWrapper {
    queueName: string,
    channel: Channel,
    ownerObjectId: string,
}
