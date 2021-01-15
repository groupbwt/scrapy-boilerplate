import winston from "winston";
import { Logger as LoggerInterface, format, level } from "winston";

export enum levels {
    ERROR = 0,
    WARN = 1,
    INFO = 2,
    HTTP = 3,
    VERBOSE = 4,
    DEBUG = 5,
    SILLY = 6
}

export class Logger {
    public static createLogger(name: string, level: levels): LoggerInterface {
        const stringLevel = levels[level].toLowerCase();

        const transport = !!process.env.LOG_FILE && process.env.LOG_FILE.length
            ? new winston.transports.File({
                // options: { flags: 'a', encoding: 'utf8' },
                filename: 'log.log',
                level: stringLevel,
                format: winston.format.combine(
                    winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
                    this.scrapyLogFormat()
                )
            })
            : new winston.transports.Console({
                level: stringLevel,
                format: winston.format.combine(
                    winston.format.colorize(),
                    winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
                    this.scrapyLogFormat()
                )
            });

        const logger = winston.createLogger({
            level: stringLevel,
            transports: [transport],
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
            return `${timestamp} [${label}] ${level.trim().toUpperCase()}: ${message}`;
        });
    }
}
