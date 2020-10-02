export async function getRMQConnectionURI(settings) {
  const usernamePassword = `${settings.rabbitmq.username}:${settings.rabbitmq.password}`;
  const hostPort = `${settings.rabbitmq.host}:${settings.rabbitmq.port}`;
  const virtualHost = encodeURIComponent(settings.rabbitmq.virtualHost);
  return `${usernamePassword}@${hostPort}/${virtualHost}`;
}
