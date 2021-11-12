import Spider from "../core/spiders/spider";
import ExampleSpider from "./example-spider";
import RecaptchaAudioSolverSpider from "./audiocaptcha/recaptcha-audio-solver-spider";

const spiders: typeof Spider[] = [ExampleSpider, RecaptchaAudioSolverSpider];
export default spiders;
