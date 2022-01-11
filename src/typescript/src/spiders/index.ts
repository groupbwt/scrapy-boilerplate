import Spider from "../core/spiders/spider";
import ExampleSpider from "./examples/example-spider";
import RecaptchaSolverWorkerSpider from "./examples/recaptcha-solver-worker-spider";

const spiders: typeof Spider[] = [ExampleSpider, RecaptchaSolverWorkerSpider];
export default spiders;
