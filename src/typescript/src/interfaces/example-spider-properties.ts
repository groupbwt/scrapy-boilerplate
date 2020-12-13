import SettingsProperties from "./settings-properties";

export default interface ExampleSpiderProperties extends SettingsProperties {
    EXAMPLE_SPIDER_TASK_QUEUE?: string;
    EXAMPLE_SPIDER_ERROR_QUEUE?: string;
}
