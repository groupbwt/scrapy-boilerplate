import dotenv from 'dotenv';
import PM2SpiderManager from './PM2SpiderManager';


async function getRMQConnectionURI() {
  const usernamePassword = `${process.env.RABBITMQ_USERNAME}:${process.env.RABBITMQ_PASSWORD}`;
  const hostPort = `${process.env.RABBITMQ_HOST}:${process.env.RABBITMQ_PORT}`;
  const virtualHost = encodeURIComponent(process.env.RABBITMQ_VIRTUAL_HOST);
  return `${usernamePassword}@${hostPort}/${virtualHost}`;
}

async function start() {
  const RMQConnectionURI = await getRMQConnectionURI();
  const manager = new PM2SpiderManager({
    rmqConnectionURL: RMQConnectionURI,
    accountManageTasksQueue: process.env.RABBITMQ_FULL_VERSION_ACCOUNT_MANAGE_TASKS,
    accountManageResultsQueue: process.env.RABBITMQ_FULL_VERSION_ACCOUNT_MANAGE_RESULTS,

    sandbox: process.env.SANDBOX === 'true',
    headless: process.env.HEADLESS === 'true',
  });
  await manager.runLoop();
}


dotenv.config();
start().then(() => process.exit(0))
  .catch((err) => {
      console.log(err);
      process.exit(1)
    }
  );
