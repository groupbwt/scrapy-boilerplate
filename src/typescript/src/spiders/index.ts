import Spider from "../core/spiders/spider";
import ExampleSpider from "./example-spider";
import RecaptchaSolverWorkerSpider from "./recaptcha-solver-worker-spider";

const spiders: typeof Spider[] = [ExampleSpider, RecaptchaSolverWorkerSpider];
export default spiders;
