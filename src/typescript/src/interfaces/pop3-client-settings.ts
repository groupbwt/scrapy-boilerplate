
export default interface Pop3ClientSettings {
    host: string
    port: number
    emailSubjectPattern: string
    emailSenderPattern: string
    emailCodeRegexList: RegExp[]
}
