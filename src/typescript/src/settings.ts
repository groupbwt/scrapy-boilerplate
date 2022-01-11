import strToBool from "./utils/strtobool";
import { millisecond } from "./types";
import { BrowserConnectOptions, BrowserLaunchArgumentOptions, LaunchOptions, Product } from "puppeteer";
import ExampleSpiderProperties from "./interfaces/example-spider-properties";
import SettingsProperties from "./interfaces/settings-properties";
import { ProxySettings } from "./interfaces/proxy-settings";
import { RabbitSettings } from "./interfaces/rabbit-settings";

export default class Settings implements SettingsProperties, ExampleSpiderProperties {
    protected static instance: Settings;

    public readonly proxyEnabled: boolean;
    public readonly proxy: ProxySettings;

    public readonly rabbit: RabbitSettings;

    public readonly browserOptions: LaunchOptions & BrowserLaunchArgumentOptions & BrowserConnectOptions & {
        product?: Product;
        extraPrefsFirefox?: Record<string, unknown>;
    };

    public readonly captchaSolverEnabled: boolean;
    public readonly captchaSolverApiKey?: string;

    public readonly navigationTimeout: millisecond = 30000;

    public readonly pipelines: any[] = [];

    public readonly EXAMPLE_SPIDER_TASK_QUEUE: string;
    public readonly EXAMPLE_SPIDER_RESULT_QUEUE: string;
    public readonly EXAMPLE_SPIDER_ERROR_QUEUE: string;

    public readonly WIT_AI_ACCESS_KEY: string;

    public static getInstance(settingsProperties: SettingsProperties = {}): Settings {
        if (!this.instance) {
            this.instance = new this();
            Object.assign(this.instance, settingsProperties);
        }

        return Object.freeze(this.instance);
    }

    protected constructor() {
        this.proxyEnabled = strToBool(process.env.PUPPETEER_PROXY_ENABLED);

        if (this.proxyEnabled) {
            const [host, port] = process.env.PUPPETEER_PROXY ? process.env.PUPPETEER_PROXY.split(':') : ['', ''];
            const [username, password] = process.env.PUPPETEER_PROXY_AUTH ? process.env.PUPPETEER_PROXY_AUTH.split(':') : ['', ''];
            this.proxy = { host, port, username, password };
        } else {
            this.proxy = { host: '', port: '', username: '', password: '' };
        }

        this.rabbit = {
            host: process.env.RABBITMQ_HOST ? process.env.RABBITMQ_HOST : '',
            port: process.env.RABBITMQ_PORT ? Number.parseInt(process.env.RABBITMQ_PORT) : 5672,
            username: process.env.RABBITMQ_USERNAME ? process.env.RABBITMQ_USERNAME : '',
            password: process.env.RABBITMQ_PASSWORD ? process.env.RABBITMQ_PASSWORD : '',
            vhost: process.env.RABBITMQ_VIRTUAL_HOST ? process.env.RABBITMQ_VIRTUAL_HOST : '/'
        };

        const [width, height] = [1920, 1080];
        this.browserOptions = {
            defaultViewport: { width, height },
            headless: strToBool(process.env.HEADLESS, true),
            devtools: strToBool(process.env.DEVTOOLS, false),
            args: [`--window-size=${width},${height}`]
        };

        this.captchaSolverEnabled = strToBool(process.env.CAPTCHA_SOLVER_ENABLED);
        this.captchaSolverApiKey = process.env.CAPTCHA_SOLVER_API_KEY;

        this.EXAMPLE_SPIDER_TASK_QUEUE = process.env.EXAMPLE_SPIDER_TASK_QUEUE ? process.env.EXAMPLE_SPIDER_TASK_QUEUE : 'example_spider_task_queue';
        this.EXAMPLE_SPIDER_RESULT_QUEUE = process.env.EXAMPLE_SPIDER_RESULT_QUEUE ? process.env.EXAMPLE_SPIDER_RESULT_QUEUE : 'example_spider_result_queue';
        this.EXAMPLE_SPIDER_ERROR_QUEUE = process.env.EXAMPLE_SPIDER_ERROR_QUEUE ? process.env.EXAMPLE_SPIDER_ERROR_QUEUE : 'example_spider_error_queue';

        this.WIT_AI_ACCESS_KEY = process.env.WIT_AI_ACCESS_KEY ? process.env.WIT_AI_ACCESS_KEY : '';
    }
}
