export default interface ProcessArguments {
    spiderName: string;
    type: 'parser' | 'worker';
    [Key: string]: any;
}
