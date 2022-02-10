import {Message, Client} from 'yapople'
import HTMLParser = require('node-html-parser')

import EmailClientSettings from '../interfaces/email-client-settings'


class POP3Client {
    public startTimeStamp: number | null = null
    public minMessageTime: number | null = null
    private readonly _popConfig: EmailClientSettings
    private readonly _email: string
    private readonly _password: string

    constructor(email: string, password: string, pop_config: EmailClientSettings) {
        this._email = email
        this._password = password
        this._popConfig = pop_config
    }

    async getVerificationCode(expirationTime: number) {
        this.startTimeStamp = new Date().getTime()
        this.minMessageTime = this.startTimeStamp - 60 * 1000
        let currentTS = this.startTimeStamp

        while (currentTS < (this.startTimeStamp + expirationTime * 60000)) {
            let emailCode = await this.__checkMail()
            if (emailCode !== null) {
                return emailCode
            }
            currentTS = new Date().getTime()
            console.log('Current timestamp: ', currentTS)
        }
        return new Error('Verification code has been expired')
    }

    getLastMessagesNumbers(messagesCount: number, limit: number = 5) {
        return Array.from(Array(messagesCount).keys()).map(v => v + 1).reverse().slice(0, Math.min(messagesCount, limit))
    }

    async __checkMail() {
        const client = new Client({
            host: this._popConfig.host,
            port: this._popConfig.port,
            tls: true,
            mailparser: true,
            username: this._email,
            password: this._password,
            options: {
                rejectUnauthorized: false,
            }
        })
        await client.connect()
        console.log('Connected')
        const count = await client.count()
        const messageNumbers = this.getLastMessagesNumbers(count)
        console.log('messageNumbers', messageNumbers)
        const messages = await client.retrieve(messageNumbers)
        const emailCode = this.__extractCode(messages)
        await client.quit()
        return emailCode
    };

    async __extractCode(messages: Message[]) {
        if (!!messages) {
            let code: string | null = null
            messages.reverse().some((message: Message) => {
                if (message.date.getTime() >= this.minMessageTime!) {
                    if (
                        String(Array.from(message.from).shift()!.address).includes(this._popConfig.emailSenderPattern)
                        && message.subject.includes(this._popConfig.emailSubjectPattern)
                    ) {
                        console.log(`Message with email pattern "${this._popConfig.emailSenderPattern}" found`)
                        console.log('Trying to get code...')
                        const html = HTMLParser.parse(message.html)
                        code = html.querySelector("div[dir='3D\"ltr\"\']")!.innerText
                        if (!code) {
                            console.log('Code not found')
                        }
                        return code != null
                    }
                }
            })
            return code
        }
        return null
    }
}

export default POP3Client
