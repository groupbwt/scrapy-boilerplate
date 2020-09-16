import dotenv from 'dotenv';


async function getRMQConnectionURI() {
  const usernamePassword = `${process.env.RABBITMQ_USERNAME}:${process.env.RABBITMQ_PASSWORD}`;
  const hostPort = `${process.env.RABBITMQ_HOST}:${process.env.RABBITMQ_PORT}`;
  const virtualHost = encodeURIComponent(process.env.RABBITMQ_VIRTUAL_HOST);
  return `${usernamePassword}@${hostPort}/${virtualHost}`;
}

async function start() {
  const RMQConnectionURI = await getRMQConnectionURI();
  // create spider instance and run as worker here
}


dotenv.config();
start().then(() => process.exit(0))
  .catch((err) => {
      console.log(err);
      process.exit(1)
    }
  );
