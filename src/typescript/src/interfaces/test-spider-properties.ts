import SettingsProperties from "./settings-properties";

export default interface TestSpiderProperties extends SettingsProperties {
    TEST_SPIDER_TASK_QUEUE?: string;
    TEST_SPIDER_ERROR_QUEUE?: string;
}
