import winston from "winston";
import { Logger as LoggerInterface, format } from "winston";

export enum levels {
    DEBUG,
    INFO,
    WARN,
    // TODO: WARNING
    ERROR,
    CRITICAL
}

export class Logger {
    public static createLogger(name: string, level: levels): LoggerInterface {
        const stringLevel = levels[level].toLowerCase();

        const consoleTransport = new winston.transports.Console({
            level: stringLevel,
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
                this.scrapyLogFormat()
            )
        });

        const logger = winston.createLogger({
            level: stringLevel,
            transports: [consoleTransport],
        });

        return logger.child({
            label: name
        });
    }

    private static getFormat() {
        return winston.format.printf(({ level, message, label, timestamp }) => {
            message = typeof message === "object" ? JSON.stringify(message, null, 4) : message;
            return `${timestamp} ${label ? `[${label}]` : ""} ${level.toUpperCase()}: ${message}`;
        });
    }

    private static scrapyLogFormat() {
        return format.printf(({ level, message, label, timestamp }) => {
            return `${timestamp} [${label}] ${level.toUpperCase()}: ${message}`
        });
    }
}
