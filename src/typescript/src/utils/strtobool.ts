export default function strToBool(str: string | undefined | null, _default: boolean = false): boolean {
    if (!str) {
        return false;
    }
    switch (str.toLowerCase().trim()) {
        case 'true':
        case 'yes':
        case '1':
            return true;
        case 'false':
        case 'no':
        case '0':
            return false;
        default:
            return _default;
    }
}
