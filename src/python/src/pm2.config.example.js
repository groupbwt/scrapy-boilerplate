const projectPrefix = 'SB'  // JIRA project prefix (for bwt deployments) or empty string for cloud/client deployments
const poetryPath = '/usr/local/bin/poetry'  // path to project poetry executable
const interpreterPath = '/bin/bash'  // path to deployment target bash executable
const maxRestarts = 5  // number of pm2 script restarts
const maxMemoryRestart = '128M' // memory max limit per process

const producers = [
  {
    name: `${projectPrefix}_product_tasks_producer`,  // replace with own command name and corresponding command executable for interpreter args
    interpreter_args: `-c '${poetryPath} run scrapy product_tasks_producer -m worker'`,
    instances: 1,
  },
]

const consumers = [
  {
    name: `${projectPrefix}_product_replies_consumer`,
    interpreter_args: `-c '${poetryPath} run scrapy product_replies_consumer -m worker'`,
    instances: 1,
  },
  {
    name: `${projectPrefix}_product_results_consumer`,
    interpreter_args: `-c '${poetryPath} run scrapy product_results_consumer -m worker'`,
    instances: 1,
  },
]

const spiders = [
  {
    name: `${projectPrefix}_products_spider`,
    interpreter_args: `-c '${poetryPath} run scrapy crawl products'`,
    instances: 2,
    max_memory_restart: '256M'
  },
]

const commands = [
  {
    name: `${projectPrefix}_product_status_reset_command`,
    interpreter_args: `-c '${poetryPath} run scrapy product_status_reset'`,
    instances: 1,
    max_memory_restart: '256M',
    cron_restart: '30 */12 * * *'
  },
]


const processNames = []
const apps = []
Array.from([producers, consumers, spiders, commands]).map(t => {
  t.reduce((a, v) => {
    if (!v.hasOwnProperty('name') || v.name.length === 0) return a
    if (processNames.includes(v.name)) {
      console.error(`Duplicate process name declared: ${v.name}. Check required`)
      process.exit(1)
    }
    processNames.push(v.name)
    a.push(
      Object.assign(
        {},
        {
          name: v.name,
          cwd: (v.hasOwnProperty('cwd')) ? v.cwd : ".",
          interpreter: (v.hasOwnProperty('interpreter')) ? v.interpreter : interpreterPath,
          interpreter_args: v.interpreter_args,
          script: (v.hasOwnProperty('script')) ? v.script : interpreterPath,
          watch: (v.hasOwnProperty('watch')) ? v.watch : false,
          instances: v.instances,
          max_memory_restart: (v.hasOwnProperty('max_memory_restart')) ? v.max_memory_restart : maxMemoryRestart,
          combine_logs: true,
          merge_logs: true,
          error_file: `./logs/${v.name}.log`,
          out_file: `./logs/${v.name}.log`,
          max_restarts: (v.hasOwnProperty('max_restarts')) ? v.max_restarts : maxRestarts,
        },
        (v.hasOwnProperty('cron_restart')) ? {
          cron_restart: v.cron_restart,
          autorestart: false,
        } : null
      )
    )
    return a
  }, apps)
})

module.exports = {
  apps: apps
}
