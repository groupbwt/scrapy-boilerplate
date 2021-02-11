import dotenv from "dotenv";

export function loadDotEnv(): string {
    let searchValue;
    let replaceValue;

    if (process.cwd().includes('/var/app')) {
        searchValue = /(.*)\/build/gi;
        replaceValue = '$1/.env';
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

    if (!!process.env.LOG_LEVEL && process.env.LOG_LEVEL.toUpperCase() == 'WARNING') {
        process.env.LOG_LEVEL = 'WARN';
    }

    return pathToEnvFile;
}
