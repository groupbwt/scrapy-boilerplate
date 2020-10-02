import {Client} from 'yapople'

import pauseFor from "./pause";
import { logger } from '../logging'


export default class POP3Client {
  constructor(email, password, pop_config) {
    this._email = email;
    this._password = password;
    this._pop_config = pop_config;
  }

  async __checkMail(startTS) {
    return new Promise((resolve, reject) => {
      const client = new Client({
        hostname: this._pop_config.host,
        port: this._pop_config.port,
        tls: false,
        mailparser: true,
        username: this._email,
        password: this._password
      });

      logger.info('startTS: %s', startTS);
      const threshold = 60 * 1000;
      // const threshold = 2 * 60 * 60 * 1000;

      client.connect(() => {
        client.count((countError, cnt) => {
          const messageNumbers = Array.from(Array(cnt).keys()).map(v => v + 1).reverse()
            .slice(0, Math.min(cnt, 10));
          logger.info("messageNumbers %s", messageNumbers);
          client.retrieve(messageNumbers, (retrieveError, messages) => {
            logger.info("messageNumbers: %s", messages.length);
            const emailCode = messages.reverse().reduce((code, message) => {
              if (code !== null) {
                return code;
              }
              logger.info("%s %s %s", message.date.getTime(), (startTS - threshold), message.date.getTime() >= (startTS - threshold));
              if (message.date.getTime() >= (startTS - threshold)) {
                const emailSenderPattern = 'verify@'
                if (String(Array.from(message.from).shift().address).includes(emailSenderPattern)) {
                  logger.info("%s msg to check", emailSenderPattern);
                  const msgHTML = message.html;
                  const emailCodeRegex = /<strong>([A-Za-z0-9]+)<\/strong><\/td>/gms;
                  const emailCodeRegexList = [emailCodeRegex];

                  code = emailCodeRegexList.reduce((a, v) => {
                    if (a !== null) {
                      return a;
                    }
                    let extractedCode = v.exec(msgHTML);
                    if (extractedCode !== null && extractedCode.length > 1 && extractedCode[1] !== null) {
                      return extractedCode[1].trim();
                    }
                    return null;
                  }, null);
                }
              }
              return code;
            }, null);

            client.quit();
            return resolve(emailCode);
          })
        });
      });
    })
  };

  async getVerificationCode(startTS) {
    return new Promise(async (resolve, reject) => {
      this.resolve = resolve;
      this.reject = reject;

      const expirationTime = 60 * 1000;
      let currentTS = startTS;

      while (currentTS < (startTS + (2 * expirationTime))) {
        await pauseFor(5000);
        let emailCode = await this.__checkMail(startTS);
        if (emailCode !== null) {
          return resolve(emailCode);
        }
        currentTS = new Date().getTime();
        logger.info("Tick: %s", currentTS);
      }
      return reject(new Error("Task has been expired"));
    })
  }

}
