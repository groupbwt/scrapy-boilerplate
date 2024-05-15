import {Message, Client} from 'yapople'
import EmailClientFilters from '../interfaces/email-client-filters'
import {HTMLElement, parse} from 'node-html-parser'
import Pop3ClientConfig from '../interfaces/pop3-client-config'


export default class Pop3Client {
    public startTimeStamp?: number
    public minMessageTime?: number
    public emailSenderPattern?: string
    public emailSubjectPattern?: string
    public cssSelector?: string
    public readonly messageLimit: number = 5
    public debug?: (info: string) => void
    private client: Client

    constructor(config: Pop3ClientConfig) {
        this.client = new Client({
            username: config.username,
            password: config.password,
            host: config.host,
            port: config.port,
            mailparser: true,
            tls: true,
            options: {
                rejectUnauthorized: false,
            },
        })
        this.debug = config.debug
    }

    async checkMail(expirationTime: number, filters: EmailClientFilters): Promise<HTMLElement> {
        this.startTimeStamp = new Date().getTime()
        const stopTimeStamp = this.startTimeStamp + expirationTime * 60000
        this.minMessageTime = this.startTimeStamp - 60 * 1000 // set min message time one minute less than start time
        let currentTimeStamp = this.startTimeStamp

        this.emailSubjectPattern = filters.emailSubjectPattern
        this.emailSenderPattern = filters.emailSenderPattern
        this.cssSelector = filters.cssSelector

        while (currentTimeStamp < stopTimeStamp) {
            let emailCode = await this.__checkMail()
            if (emailCode !== null) {
                return emailCode
            }
            currentTimeStamp = new Date().getTime()
            currentTimeStamp < stopTimeStamp &&
            console.log(`Message expires in ${(stopTimeStamp - currentTimeStamp) / 1000} s`)
        }
        throw new Error('Verification code has been expired')
    }

    getLastMessagesNumbers(messagesCount: number): number[] {
        return Array.from(Array(messagesCount).keys(), v => v + 1)
            .reverse()
            .slice(0, Math.min(messagesCount, this.messageLimit))
    }

    testRegExp(value: string, pattern: string): boolean {
        return new RegExp(pattern, 'i').test(value)
    }

    passFilters(message: Message): boolean {
        return new Date(message.date).getTime() > this.minMessageTime! &&
            this.testRegExp(message.from[0].address, this.emailSenderPattern!) &&
            this.testRegExp(message.subject, this.emailSubjectPattern!)
    }

    getElement(message: Message): HTMLElement | null {
        const html = parse(message.html)
        const element = html.querySelector(this.cssSelector!)
        if (!element) {
            console.log('Element not found')
            return null
        }
        return element
    }

    async __checkMail(): Promise<HTMLElement | null> {
        await this.client.connect()
        this.debug && this.debug('Connected')
        const count = await this.client.count()
        const messageNumbers = this.getLastMessagesNumbers(count)
        let messages = await this.client.retrieve(messageNumbers)
        this.debug && this.debug(`Received ${messages.length} messages`)
        messages = messages.filter(Boolean).reverse()
        let element: HTMLElement | null = null
        for (let message of messages) {
            if (this.passFilters(message)) {
                this.debug && this.debug(`Passed filters message HTML ${message.html}`)
                element = this.getElement(message)
                break
            }
        }
        await this.client.disconnect()
        this.debug && this.debug('Disconnected')
        return element
    }
}
