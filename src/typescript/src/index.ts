import yargs from 'yargs';
import Crawler from "./core/crawler";
import Argv from "./interfaces/argv";
import { loadDotEnv } from "./utils/laod-dot-env";
import { Logger } from "./utils/logger";

yargs.command('crawl <spiderName>', 'run the spider', (yargs) => {
    yargs.positional('name', {
        describe: 'spider name'
    });
}, main)
    .options({
        'type': {
            type: 'string',
            default: 'parser',
            choices: ['parser', 'worker']
        }
        // 'task': {
        //     type: 'string',
        //     demandOption: true,
        //     choices: ['products', 'categories', 'keywords']
        // },
        // 'id': {
        //     type: 'number',
        //     alias: 'i',
        //     demandOption: true,
        //     default: '',
        // },
    })
    .demandCommand()
    .help()
    .argv;


async function main(argv: Argv) {
    loadDotEnv();
    await Crawler.run(argv).catch(async (err: Error) => {
        const logger = Logger.createLogger(Crawler.constructor.name);
        logger.error(err.stack ? err.stack : err);
    });
}
