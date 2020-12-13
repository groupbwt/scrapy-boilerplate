import { Frame, Page } from "puppeteer";
import sleep from "../sleep";


export async function waitForFrame(
    page: Page,
    findFrameFunction: (value: Frame, index: number, frames: Frame[]) => boolean,
    options = { timeout: 30000 }
): Promise<Frame> {
    let frame;
    let failed = false;

    const timeoutId = setTimeout(() => {
        failed = true;
    }, options.timeout);

    while (true) {
        frame = page.frames().find(findFrameFunction);
        if (frame !== undefined) {
            clearTimeout(timeoutId);
            return frame;
        }

        if (failed) {
            throw 'Frame not found';
        }

        await sleep(150);
    }
}
