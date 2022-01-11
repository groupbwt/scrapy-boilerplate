import RecaptchaSpider from "../../extensions/recaptcha-audio-solver/recaptcha-spider";

export default class RecaptchaSolverWorkerSpider extends RecaptchaSpider {
    public static spiderName: string = 'recaptcha-spider';
    public taskQueueName = this.settings.EXAMPLE_SPIDER_TASK_QUEUE;
    public resultQueueName = this.settings.EXAMPLE_SPIDER_RESULT_QUEUE;
    public cacheEnabled = true;
}
