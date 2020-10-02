import { Connection } from 'amqplib-as-promised';


export class RabbitMQRPCServerWorker {
  /**
   * @param uri
   * @param taskQueueName
   */
  constructor(uri, taskQueueName) {
    this._uri = uri;
    this._taskQueueName = taskQueueName;

    this._initStatus = false;
    this._readyToUseStatus = false;
  }

  /**
   * @returns {Promise<void>}
   */
  async __init() {
    if (!this._uri.startsWith('amqp://')) {
      this._uri = `amqp://${this._uri}`;
    }
    this._connection = new Connection(this._uri);
    await this._connection.init();
    this._channel = await this._connection.createChannel();
    this._initStatus = true;
  }

  /**
   * @returns {Promise<void>}
   */
  async connect(consumeCallback) {
    if (!this._initStatus) {
      await this.__init();
    }
    await this._channel.prefetch(1);
    await this._channel.assertQueue(this._taskQueueName, { durable: true });

    this.consumerTag = await this._channel.consume(
      this._taskQueueName,
      consumeCallback,
      {
        // noAck: true
        noAck: false
      }
    );
  }

  /**
   * @param data
   * @param targetQueue
   * @param options
   * @returns {Promise}
   */
  async sendMessage(data, targetQueue, options = {}) {
    const defaultOptions = {
      persistent: true,
      contentType: 'application/json',
    };
    const finalOptions = Object.assign({}, defaultOptions, options);
    const msg = (typeof data !== 'string') ? JSON.stringify(data) : data;
    return this._channel.sendToQueue(targetQueue, Buffer.from(msg), finalOptions);
  }

  async cancelConsumer() {
    if (this.consumerTag !== undefined) {
      if ((typeof this.consumerTag) === 'string') {
        await this._channel.cancel(this.consumerTag);
      } else if ((typeof this.consumerTag) === 'object' && this.consumerTag.hasOwnProperty("consumerTag")) {
        await this._channel.cancel(this.consumerTag.consumerTag);
      } else {
        await this._channel.cancel(this.consumerTag);
      }
      this.consumerTag = undefined;
    }
  }

  /**
   * @returns {Promise<void>}
   */
  async close() {
    await this.cancelConsumer();
    if (this._channel !== undefined) {
      await this._channel.close();
    }
    if (this._connection !== undefined) {
      await this._connection.close();
    }
    this._initStatus = false;
  }
}
