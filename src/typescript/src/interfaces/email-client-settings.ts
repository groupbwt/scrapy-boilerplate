export default interface EmailClientSettings {
    host: string
    port: number
    emailSubjectPattern: string
    emailSenderPattern: string
    emailCodeSelector: string
}
