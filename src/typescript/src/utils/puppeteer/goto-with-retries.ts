import { HTTPResponse, Page, WaitForOptions } from "puppeteer";

export default async function gotoWithRetries(
    page: Page,
    url: string,
    options?: WaitForOptions & { referer?: string; },
    maxRetries: number = 3
): Promise<HTTPResponse | null> {
    let pageLoadTries = 0;
    let lastError: Error | unknown;
    while (pageLoadTries < maxRetries) {
        try {
            return await page.goto(url, options);
        } catch (e) {
            pageLoadTries += 1;
            lastError = e;
        }
    }
    throw lastError;
}
