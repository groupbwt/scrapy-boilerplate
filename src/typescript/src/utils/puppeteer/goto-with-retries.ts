import { DirectNavigationOptions, Page, Response } from "puppeteer";

export default async function gotoWithRetries(
    page: Page,
    url: string,
    options?: DirectNavigationOptions,
    maxRetries: number = 3
): Promise<Response | null> {
    let pageLoadTries = 0;
    let lastError: Error | null = null;
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
