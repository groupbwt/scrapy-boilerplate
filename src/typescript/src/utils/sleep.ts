import { millisecond } from "../types";

export default async function sleep(timeout: millisecond): Promise<void> {
    return new Promise((resolve, reject) => {
        try {
            setTimeout(() => {
                resolve();
            }, timeout);
        } catch (e) {
            reject(e instanceof Error ? e.toString() : e);
        }
    });
}
