//@ts-ignore
import { Client } from 'yapople';

import { levels, Logger } from './logger';
import { Logger as LoggerInterface } from "winston";
import sleep from "./sleep";

interface Author {
    address: string,
}

interface Message {
    html: string;
    headers: any;
    subject: string;
    references: string[];
    messageId: string;
    inReplyTo: string[];
    priority: string;
    from: Author[];
    replyTo: object[];
    to: object[];
    date: Date;
    receivedDate: Date;
}

export default class POP3Client {
    logger: LoggerInterface;

    constructor(
        private email: string,
        private password: string,
        private pop_config: { host: string, port: string }
    ) {
        this.logger = Logger.createLogger(this.constructor.name, levels.DEBUG);
    }

    public async getVerificationCode(startTS: number): Promise<string | null> {
        return new Promise(async (resolve, reject) => {
            const expirationTime = 60 * 1000;
            let currentTS = startTS;

            while (currentTS < (startTS + (2 * expirationTime))) {
                await sleep(5000);
                let emailCode: string | null = await this.checkMail(startTS);
                if (emailCode !== null) {
                    return resolve(emailCode);
                }
                currentTS = new Date().getTime();
                this.logger.info("Tick: %s", currentTS);
            }
            return reject(new Error("Task has been expired"));
        })
    }

    private async checkMail(startTS: number): Promise<string | null> {
        return new Promise((resolve, reject) => {
            const client = new Client({
                hostname: this.pop_config.host,
                port: this.pop_config.port,
                tls: false,
                mailparser: true,
                username: this.email,
                password: this.password
            });

            this.logger.info('startTS: %s', startTS);
            const threshold = 60 * 1000;
            // const threshold = 2 * 60 * 60 * 1000;

            client.connect(() => {
                client.count((countError: Error, cnt: number) => {
                    const messageNumbers = Array.from(Array(cnt).keys())
                        .map(v => v + 1)
                        .reverse()
                        .slice(0, Math.min(cnt, 10));

                    this.logger.info("messageNumbers %s", messageNumbers);
                    client.retrieve(messageNumbers, (retrieveError: Error, messages: Array<Message>) => {
                        this.logger.info("messageNumbers: %s", messages.length);
                        const emailCode = messages.reverse().reduce((code: any, message) => {
                            if (code !== null) {
                                return code;
                            }
                            this.logger.info("%s %s %s", message.date.getTime(), (startTS - threshold), message.date.getTime() >= (startTS - threshold));
                            if (message.date.getTime() >= (startTS - threshold)) {
                                const emailSenderPattern = 'verify@';
                                const content: Array<Author> = Array.from(message.from);
                                if (content.length && String(content.shift()!.address).includes(emailSenderPattern)) {
                                    this.logger.info("%s msg to check", emailSenderPattern);
                                    const msgHTML: string = message.html;
                                    const emailCodeRegex = /<strong>([A-Za-z0-9]+)<\/strong><\/td>/gms;
                                    const emailCodeRegexList = [emailCodeRegex];

                                    //@ts-ignore
                                    code = emailCodeRegexList.reduce((a, v) => {
                                        if (a !== null) {
                                            return a;
                                        }
                                        let extractedCode = v.exec(msgHTML);
                                        if (extractedCode !== null && extractedCode.length > 1 && extractedCode[1] !== null) {
                                            return extractedCode[1].trim();
                                        }
                                        return null;
                                    }, null);
                                }
                            }
                            return code;
                        }, null);

                        client.quit();
                        return resolve(emailCode);
                    })
                });
            });
        })
    };
}
