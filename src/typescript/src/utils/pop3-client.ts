import {Message, Client} from 'yapople'

import Pop3ClientSettings from '../interfaces/pop3-client-settings'


class POP3Client {
    public startTimeStamp: number | null = null
    public minMessageTime: number | null = null
    private readonly _pop_config: Pop3ClientSettings
    private readonly _email: string
    private readonly _password: string

    constructor(email: string, password: string, pop_config: Pop3ClientSettings) {
        this._email = email
        this._password = password
        this._pop_config = pop_config
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
            host: this._pop_config.host,
            port: this._pop_config.port,
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
            return messages.reverse().reduce((code: null | string, message) => {
                if (code !== null) {
                    return code
                }
                if (message.date.getTime() >= this.minMessageTime!) {
                    if (String(Array.from(message.from).shift()!.address).includes(this._pop_config.emailSenderPattern)) {
                        console.log(`Message with email pattern "${this._pop_config.emailSenderPattern}" found`)
                        console.log('Trying to get code...')
                        code = this.__executeRegExpList(message.html)
                    }
                }
                return code
            }, null)
        }
        return null
    }

    __executeRegExpList(html: string): string | null {
        let extractedCode: string | null = null
        this._pop_config.emailCodeRegexList.some((regexp: RegExp) => {
            const match = regexp.exec(html)
            if (match !== null && match.length > 1 && match[1] !== null) {
                console.log('Code found')
                extractedCode = match[1].trim()
                return true
            }
        })
        return extractedCode
    }
}

export default POP3Client
