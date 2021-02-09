const projectPrefix = 'SB'  // JIRA project prefix (for bwt deployments) or empty string for cloud/client deployments
const interpreterPath = 'node'  // path to deployment target bash executable
const maxRestarts = 5  // number of pm2 script restarts
const maxMemoryRestart = '512M' // memory max limit per process


const spiders = [
  {
    name: `${projectPrefix}_auth_spider`,
    script: `auth.js`,
    instances: 2,
  },
]

const commands = [
  {
    name: `${projectPrefix}_accounts_manager`,
    script: `index.js`,
    instances: 1,
    max_memory_restart: '256M',
  },
]


const processNames = []
const apps = []
Array.from([spiders, commands]).map(t => {
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
          cwd: (v.hasOwnProperty('cwd')) ? v.cwd : "./build/",
          interpreter: (v.hasOwnProperty('interpreter')) ? v.interpreter : interpreterPath,
          interpreter_args: (v.hasOwnProperty('interpreter_args')) ? v.interpreter_args : '',
          script: (v.hasOwnProperty('script')) ? v.script : 'index.js',
          watch: (v.hasOwnProperty('watch')) ? v.watch : false,
          instances: v.instances,
          max_memory_restart: (v.hasOwnProperty('max_memory_restart')) ? v.max_memory_restart : maxMemoryRestart,
          combine_logs: true,
          merge_logs: true,
          error_file: (v.hasOwnProperty('cwd')) ? `${v.cwd}/logs/${v.name}.log` : `../logs/${v.name}.log`,
          out_file: (v.hasOwnProperty('cwd')) ? `${v.cwd}/logs/${v.name}.log` : `../logs/${v.name}.log`,
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
