import {SocksClient} from 'socks'
import {HTMLElement, parse} from 'node-html-parser'
import quotedPrintable from 'quoted-printable'
import Imap from 'imap'
import utf8 from 'utf8'


import ImapConnection from './imap-connection'
import ImapClientMessage from '../interfaces/imap-client-message'
import Settings from '../settings'
import {loadDotEnv} from './load-dot-env'
import ImapClientConfig from "../interfaces/imap-client-config";
import ImapClientFilters from "../interfaces/imap-client-filters";


export default class ImapClient {
    public startTimeStamp: number | null = null
    public minMessageTime: number | null = null
    public emailSenderPattern: string | undefined = undefined
    public emailSubjectPattern: string | undefined = undefined
    public cssSelector: string | undefined = undefined
    public readonly messageLimit: number
    public readonly settings: Settings

    private readonly _imapConfig: ImapClientConfig

    constructor(imapConfig: ImapClientConfig) {
        loadDotEnv()
        this.messageLimit = 5
        this.settings = Settings.getInstance()
        this._imapConfig = {
            user: imapConfig.user,
            password: imapConfig.password,
            host: imapConfig.host,
            port: imapConfig.port,
            tls: true,
            tlsOptions: {
                rejectUnauthorized: false,
            },
        }
    }

    async checkMail(expirationTime: number, filters: ImapClientFilters): Promise<HTMLElement> {
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

    openMailbox(imap: Imap, mailboxName: string, cb: (err: Error, box: Imap.Box) => void) {
        imap.openBox(mailboxName, true, cb)
    }

    async __checkMail(): Promise<HTMLElement | null> {
        let messageObjects: ImapClientMessage[] = []
        if (this.settings.imapProxyEnabled) {
            const socksConnection = await this.__getSocksConnection()
            this._imapConfig.socket = socksConnection.socket
        }

        const imapClient = new ImapConnection(this._imapConfig)
        imapClient.connect()

        return new Promise(((resolve: (value: HTMLElement | null) => void, reject) => {
            imapClient.once('ready', () => {
                this.openMailbox(imapClient, 'INBOX', (err, box) => {
                    if (err) throw err

                    const messages = imapClient.seq.fetch(`${box.messages.total - this.messageLimit + 1}:*`, {
                        bodies: ['HEADER.FIELDS (FROM SUBJECT DATE)', 'TEXT'],
                        struct: true
                    })

                    messages.on('message', ((message, seqno) => {
                        let messageObject: ImapClientMessage = {}

                        message.on('body', ((stream, info) => {
                            if (info.which === 'HEADER.FIELDS (FROM SUBJECT DATE)') {
                                let buffer = ''

                                stream.on('data', (chunk) => {
                                    buffer += chunk.toString()
                                })

                                stream.once('end', () => {
                                    messageObject.number = seqno
                                    messageObject.header = Imap.parseHeader(buffer)
                                })
                            } else if (info.which === 'TEXT') {
                                let buffer = ''

                                stream.on('data', (chunk) => {
                                    buffer += chunk.toString()
                                })

                                stream.once('end', () => {
                                    messageObject.body = buffer
                                })
                            }
                        }))

                        message.once('attributes', attrs => {
                            messageObject.attrs = attrs
                        })

                        message.once('end', () => {
                            if (this.__passFilters(messageObject)) {
                                messageObject.body = this.decodeMessage(messageObject)
                                messageObjects.push(messageObject)
                            }
                        })
                    }))
                    messages.on('end', () => {
                        imapClient.end()
                        console.log('Found %d messages', messageObjects.length)

                        resolve(this.__getElement(messageObjects))
                    })

                })
            })
            imapClient.once('error', function (err: Error) {
                reject(err)
            })
        }))
    }

    decodeMessage(message: ImapClientMessage) {
        const encoding = this.__getEncoding(message)
        switch (encoding) {
            case '7bit':
            case '8bit':
                return message.body
            case 'quoted-printable':
                return utf8.decode(quotedPrintable.decode(message.body!))
            default:
                throw new Error('Unknown encoding')
        }
    }

    __getEncoding(message: ImapClientMessage): string {
        let encoding: string | null = null
        if (message.attrs!.struct.length == 1) {
            throw new Error('Received multipart message')
        }
        message.attrs!.struct.some((messagePart: any) => {
            if (messagePart instanceof Array) {
                messagePart.some(messageSubPart => {
                    if (messageSubPart.type === 'text' && messageSubPart.subtype === 'html') {
                        encoding = messageSubPart.encoding.toLowerCase()
                    }
                    return encoding != null
                })
            }
        })
        if (!encoding) {
            throw new Error('Could not get message encoding')
        }
        return encoding
    }

    __passFilters(message: ImapClientMessage) {
        return new Date(message.header!.date[0]).getTime() > this.minMessageTime! &&
            message.header!.from[0].trim().toLowerCase().includes(this.emailSenderPattern!.trim().toLowerCase()) &&
            message.header!.subject[0].trim().toLowerCase().includes(this.emailSubjectPattern!.trim().toLowerCase())
    }

    __getElement(messages: ImapClientMessage[]): HTMLElement | null {
        if (!!messages) {
            let element: HTMLElement | null | undefined = null
            messages.reverse().some((message: ImapClientMessage) => {
                const html = parse(message.body!)
                element = html.querySelector(this.cssSelector!)
                if (!element) {
                    console.log('Element not found')
                }
                return element != null
            })
            return element
        }
        return null
    }

    async __getSocksConnection() {
        return await SocksClient.createConnection({
            proxy: {
                host: this.settings.imapProxy.host, // ipv4 or ipv6 or hostname
                port: parseInt(this.settings.imapProxy.port),
                type: 5, // Proxy version (4 or 5)
                userId: this.settings.imapProxy.username,
                password: this.settings.imapProxy.password,
            },
            command: 'connect', // SOCKS command (createConnection factory function only supports the connect command)
            destination: {
                host: this._imapConfig.host!,
                port: this._imapConfig.port!,
            },
        })
    }
}
