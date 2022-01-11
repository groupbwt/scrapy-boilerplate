import { Frame, Page, WaitForSelectorOptions } from "puppeteer";

export async function waitForFrame(
    page: Page,
    selector: string,
    options: WaitForSelectorOptions = {}
): Promise<Frame> {
    const element = (await page.waitForSelector(selector, options))!;
    const result = await element.contentFrame();
    if (result) {
        return result;
    } else {
        throw new Error('extracted element is not a frame');
    }
}
