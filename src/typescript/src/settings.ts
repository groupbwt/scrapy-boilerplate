import dotenv from 'dotenv';
import strToBool from "./utils/strtobool";
import { millisecond } from "./types";
import { LaunchOptions } from "puppeteer";
import TestSpiderProperties from "./interfaces/test-spider-properties";
import SettingsProperties from "./interfaces/settings-properties";
import { ProxySettings } from "./interfaces/proxy-settings";
import { RabbitSettings } from "./interfaces/rabbit-settings";

export default class Settings implements SettingsProperties, TestSpiderProperties {
    protected static instance: Settings;

    public readonly proxyEnabled: boolean;
    public readonly proxy: ProxySettings;

    public readonly rabbit: RabbitSettings;

    public readonly browserOptions: LaunchOptions;

    public readonly captchaSolverEnabled: boolean;
    public readonly captchaSolverApiKey?: string;

    public readonly navigationTimeout: millisecond = 30000;

    public readonly pipelines: any[] = [];

    public readonly TEST_SPIDER_TASK_QUEUE: string;
    public readonly TEST_SPIDER_ERROR_QUEUE: string;

    public static getInstance(settingsProperties: SettingsProperties = {}): Settings {
        if (!this.instance) {
            this.instance = new this();
            Object.assign(this.instance, settingsProperties);
        }

        return Object.freeze(this.instance);
    }

    protected constructor() {
        Settings.loadDotEnv();

        this.proxyEnabled = strToBool(process.env.PROXY_ENABLED);

        if (strToBool(process.env.PUPPETEER_PROXY_ENABLED)) {
            const [host, port] = process.env.PUPPETEER_PROXY ? process.env.PUPPETEER_PROXY.split(':') : ['', ''];
            const [username, password] = process.env.PROXY_AUTH ? process.env.PROXY_AUTH.split(':') : ['', ''];
            this.proxy = { host, port, username, password };
        } else {
            const [host, port] = process.env.PROXY ? process.env.PROXY.split(':') : ['', ''];
            const [username, password] = process.env.PUPPETEER_PROXY_AUTH ? process.env.PUPPETEER_PROXY_AUTH.split(':') : ['', ''];
            this.proxy = { host, port, username, password };
        }

        this.rabbit = {
            host: process.env.RABBITMQ_HOST ? process.env.RABBITMQ_HOST : '',
            port: process.env.RABBITMQ_PORT ? Number.parseInt(process.env.RABBITMQ_PORT) : 5672,
            username: process.env.RABBITMQ_USERNAME ? process.env.RABBITMQ_USERNAME : '',
            password: process.env.RABBITMQ_PASSWORD ? process.env.RABBITMQ_PASSWORD : '',
            vhost: process.env.RABBITMQ_VIRTUAL_HOST ? process.env.RABBITMQ_VIRTUAL_HOST : '/',
        };

        this.browserOptions = {
            headless: strToBool(process.env.HEADLESS),
            devtools: strToBool(process.env.DEVTOOLS, false),
            args: []
        };

        this.captchaSolverEnabled = strToBool(process.env.CAPTCHA_SOLVER_ENABLED);
        this.captchaSolverApiKey = process.env.CAPTCHA_SOLVER_API_KEY;

        this.TEST_SPIDER_TASK_QUEUE = process.env.TEST_SPIDER_TASK_QUEUE ? process.env.TEST_SPIDER_TASK_QUEUE : 'test_spider_task_queue';
        this.TEST_SPIDER_ERROR_QUEUE = process.env.TEST_SPIDER_ERROR_QUEUE ? process.env.TEST_SPIDER_ERROR_QUEUE : 'test_spider_error_queue';
    }

    private static loadDotEnv() {
        let searchValue;
        let replaceValue;

        if (process.cwd().includes('/var/app')) {
            searchValue = /(.*)\/build/gi;
            replaceValue = '$1\\.env';
        } else if (process.platform === "win32") {
            searchValue = /(.*)\\src\\typescript.*/gi;
            replaceValue = '$1\\.env';
        } else {
            searchValue = /(.*)\/src\/typescript.*/gi;
            replaceValue = '$1\/.env';
        }

        const pathToEnvFile = process.cwd().replace(searchValue, replaceValue);
        const result = dotenv.config({ path: pathToEnvFile });

        if (result.error) {
            throw result.error;
        }
    }
}
