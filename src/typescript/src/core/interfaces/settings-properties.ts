import { millisecond } from "../../types";
import { LaunchOptions } from "puppeteer";
import { ProxySettings } from "./proxy-settings";
import { RabbitSettings } from "./rabbit-settings";

export default interface SettingsProperties {
    proxyEnabled?: boolean;
    proxy?: ProxySettings;

    rabbit?: RabbitSettings;

    browserOptions?: LaunchOptions;

    captchaSolverEnabled?: boolean;
    captchaSolverApiKey?: string;

    navigationTimeout?: millisecond,

    pipelines?: Array<object>
}
