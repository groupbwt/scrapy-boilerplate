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

    getLastMessagesNumbers(messagesCount: number) {
        return Array.from(Array(messagesCount).keys(), v => v + 1)
            .reverse()
            .slice(0, Math.min(messagesCount, this.messageLimit))
    }

    checkStringIncludes(value: string, pattern: string) {
        return value.trim().toLowerCase().includes(pattern.trim().toLowerCase())
    }

    passFilters(message: Message) {
        return new Date(message.date).getTime() > this.minMessageTime! &&
            this.checkStringIncludes(message.from[0].address, this.emailSenderPattern!) &&
            this.checkStringIncludes(message.subject, this.emailSubjectPattern!)
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

    async __checkMail() {
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

const client = new Pop3Client({
    username: 'halimov_oa@groupbwt.com',
    password: 'Onelove1999',
    host: 'pop.gmail.com',
    port: 995,
    debug: (info) => console.log(info),
})

client.checkMail(3, {
    emailSubjectPattern: 'password',
    emailSenderPattern: '@amazon.com',
    cssSelector: 'p.otp',
}).then(result => {
    console.log(result)
}).catch(err => console.log(err))

