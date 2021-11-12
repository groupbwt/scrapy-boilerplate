import RmqPipeline from "../../pipelines/rmq-pipeline";

import ExampleSpiderProperties from "../../interfaces/example-spider-properties";
import BaseRecaptchaAudioSolverSpider from "./base-recaptcha-audio-solver-spider";


export default class RecaptchaAudioSolverSpider extends BaseRecaptchaAudioSolverSpider {
    public static spiderName: string = 'recaptcha-audio-solver';
    public taskQueueName = this.settings.EXAMPLE_SPIDER_TASK_QUEUE;

    getCustomSettingsProperties(): ExampleSpiderProperties {
        return {
            pipelines: [
                RmqPipeline
            ]
        };
    }
}
