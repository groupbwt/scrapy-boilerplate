import {YapopleClientConfig} from 'yapople'


export default interface Pop3ClientConfig extends YapopleClientConfig {
    debug?: (info: string) => void
}
