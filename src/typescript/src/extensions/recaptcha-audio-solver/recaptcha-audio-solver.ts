import { ElementHandle, Frame, HTTPResponse, Page } from "puppeteer";
import { waitForFrame } from "../../utils/puppeteer/wait-for-frame";
import WitAi from "../../utils/wit-ai";
import { Logger } from "../../utils/logger";
import winston from "winston";
import fs from "fs";
import path from "path";

export default class RecaptchaAudioSolver {
    private readonly logger: winston.Logger;
    private readonly witAiAccessKey: string;
    private readonly saveDirectory: string | null;

    constructor(witAiAccessKey: string, saveDirectory?: string) {
        this.logger = Logger.createLogger(this.constructor.name);
        this.witAiAccessKey = witAiAccessKey;
        this.saveDirectory = saveDirectory && fs.existsSync(saveDirectory) ? saveDirectory : null;
    }

    public async solve(page: Page): Promise<string> {
        this.logger.info('start solving audiocaptcha');
        const [isSolved, captchaUIFrame, captchaContentFrameOrNull, audioResponsePromise] = await this.openAudioCaptchaModalWindow(page);
        if (isSolved) {
            audioResponsePromise.catch(e => null);
        } else {
            const captchaContentFrame = captchaContentFrameOrNull!;

            const responseOrErrorSelector = await Promise.race([
                audioResponsePromise,
                captchaContentFrame.waitForSelector('.rc-doscaptcha-body-text', { visible: true }) as Promise<ElementHandle>
            ]);
            if (this.isHTTPResponse(responseOrErrorSelector)) {
                const audioBuffer = await responseOrErrorSelector.buffer();
                const audioMessage = await this.speechAudio(page, audioBuffer);
                await this.enterAudioMessage(audioMessage, captchaContentFrame, captchaUIFrame);
                this.saveAudioToDirectory(page, audioMessage, audioBuffer);
            } else {
                const message = await captchaContentFrame.evaluate(e => e.textContent, responseOrErrorSelector);
                throw new Error(`an error message is received when solving the captcha (1): "${message}"`);
            }
        }

        const gRecaptchaResponse = await page.evaluate(() => {
            return (document.querySelector('.g-recaptcha-response') as HTMLTextAreaElement).value;
        });
        this.logger.info(`audiocaptcha solved.`);
        return gRecaptchaResponse;
    }

    private async openAudioCaptchaModalWindow(page: Page): Promise<[boolean, Frame, Frame | null, Promise<HTTPResponse>]> {
        const captchaUISelector = 'iframe[src*="google.com/recaptcha/"][src*="/anchor"]';
        const captchaElement = await page.waitForSelector(captchaUISelector, { visible: true });
        const captchaUIFrame = await waitForFrame(page, captchaUISelector, { visible: true });
        const checkButton = await captchaUIFrame.waitForSelector('.recaptcha-checkbox-border:not(style)', { visible: true });
        await page.evaluate(frame => frame.scrollIntoView(), captchaElement);
        await captchaUIFrame.evaluate(e => e.click(), checkButton);

        const captchaContentFrame = await Promise.race([
            waitForFrame(page, 'iframe[src*="google.com/recaptcha/"][src*="/bframe"]', { visible: true }),
            captchaUIFrame.waitForSelector('.recaptcha-checkbox-checked', { visible: true }) as Promise<ElementHandle>
        ]);

        const audioResponsePromise: Promise<HTTPResponse> = page.waitForResponse(res => {
            return res.url().includes('recaptcha/api2/payload') && res.headers()['content-type'] === 'audio/mp3';
        });
        if (this.isFrame(captchaContentFrame)) {
            await Promise.race([
                captchaContentFrame.waitForSelector('#recaptcha-image-button:not([style])', { visible: true }),
                captchaContentFrame.waitForSelector('#recaptcha-audio-button:not([style])', { visible: true })
            ]);

            const changeToAudioButton = await captchaContentFrame.$('#recaptcha-audio-button:not([style])');
            if (!!changeToAudioButton) {
                await captchaContentFrame.evaluate(e => e.click(), changeToAudioButton);
            }

            return [false, captchaUIFrame, captchaContentFrame, audioResponsePromise];
        } else {
            this.logger.info('solved without captcha');
            return [true, captchaUIFrame, null, audioResponsePromise];
        }
    }

    private async speechAudio(page: Page, audioBuffer: Buffer): Promise<string> {
        const message = await WitAi.speechAudio(audioBuffer, this.witAiAccessKey);
        if (message.trim().length === 0) {
            this.saveAudioToDirectory(page, `error`, audioBuffer);
            throw new Error('Wit.ai returns an empty message');
        }
        return message;
    }

    private async enterAudioMessage(audioMessage: string, captchaContentFrame: Frame, captchaUIFrame: Frame): Promise<void> {
        const enterMessageElement = (await captchaContentFrame.waitForSelector('#audio-response', { visible: true }))!;
        await enterMessageElement.type(audioMessage);

        const verifyButton = await captchaContentFrame.waitForSelector('#recaptcha-verify-button', { visible: true });
        await captchaContentFrame.evaluate(e => e.click(), verifyButton);

        const errorMessageSelector = '.rc-audiochallenge-error-message, .rc-doscaptcha-body-text';
        const captchaCheckboxCheckedSelector = '.recaptcha-checkbox-checked';
        await Promise.race([
            captchaUIFrame.waitForSelector(captchaCheckboxCheckedSelector, { visible: true }),
            captchaContentFrame.waitForSelector(errorMessageSelector, { visible: true })
        ]);

        if (!await captchaUIFrame.$(captchaCheckboxCheckedSelector)) {
            const errorElementHandle = await captchaContentFrame.$(errorMessageSelector);
            const message = await captchaContentFrame.evaluate(e => e.textContent, errorElementHandle);
            throw new Error(`an error message is received when solving the captcha (2): message="${message}". audioMessage="${audioMessage}"`);
        }
    }

    private saveAudioToDirectory(page: Page, audioMessage: string, audioBuffer: Buffer): void {
        if (this.saveDirectory) {
            const domain = new URL(page.url()).hostname;
            const filename = `${domain} ${Date.now().toString()} ${audioMessage}`;
            const filePath = path.join(this.saveDirectory, `${this.textToSlug(filename)}.mp3`);
            fs.writeFileSync(filePath, audioBuffer, {});
        }
    }

    private textToSlug(text: string): string {
        return text.toLowerCase().replace(/[^\w ]+/g, '').replace(/ +/g, '-');
    }

    private isHTTPResponse(obj: HTTPResponse | ElementHandle): obj is HTTPResponse {
        return (<HTTPResponse>obj).request !== undefined;
    }

    private isFrame(obj: Frame | ElementHandle): obj is Frame {
        return (<Frame>obj).goto !== undefined;
    }
}
