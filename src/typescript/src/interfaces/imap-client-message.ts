export default interface ImapClientMessage {
    number?: number
    header?: {[index: string]: string[]}
    body?: string
    attrs?: {[key: string]: any}
}
