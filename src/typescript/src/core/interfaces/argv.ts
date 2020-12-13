export default interface Argv {
    spiderName: string;
    type: 'parser' | 'worker';
    [Key: string]: any;
}
