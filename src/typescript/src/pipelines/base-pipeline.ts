import { Logger } from "../utils/logger";
import OutputItem from "../items/output-item/output-item";
import Settings from "../settings";
import Argv from "../interfaces/argv";
import Spider from "../core/spiders/spider";
import { Message } from "amqplib";

export default abstract class BasePipeline {
    public logger = Logger.createLogger(this.constructor.name);

    public constructor(
        protected spider: Spider,
        protected argv: Argv,
        protected settings: Settings
    ) {
        //
    }

    abstract init(): Promise<void>;

    abstract process(item: OutputItem, msg?: Message): Promise<OutputItem | null>;

    abstract close(): Promise<void>;
}
