
export default interface Pop3ClientSettings {
    host: string
    port: number
    emailSenderPattern: string
    emailCodeRegexList: RegExp[]
}
