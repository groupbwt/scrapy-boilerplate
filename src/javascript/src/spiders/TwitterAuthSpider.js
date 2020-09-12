import TwitterBaseSpider from "./TwitterBaseSpider";
import POP3Client from "../utils/POP3Client";


class TwitterAuthSpider extends TwitterBaseSpider {
  constructor(credentials, headless = false, ruCaptchaKey = null) {
    super(headless, ruCaptchaKey, {
      host: credentials['host'],
      port: credentials['port'],
      username: credentials['proxies.username'],
      password: credentials['proxies.password']
    });

    this._isInitCompleted = false;
    this._credentials = credentials;
    this._headless = headless;

    this._emailClient = null;
  };

  async _login() {
    await this.goWithRetries('https://twitter.com/', 2);
    let currentURL = await this._page.url();
    if (currentURL.includes('/home') || (await this._page.$('a[href="/login"]') === null)) {
      return true;
    }
    await this.goWithRetries('https://twitter.com/login', 2);
    await this._page.type('input[name="session[username_or_email]"]', this._credentials?.username, {delay: 75});
    await this._page.type('input[name="session[password]"]', this._credentials?.password, {delay: 75});
    const startLoginTS = (new Date()).getTime();
    await this._page.waitFor(500);
    try {
      await this._page.clickAndWaitForNavigation('div[data-testid="LoginForm_Login_Button"]')
    } catch (e) {
      // pass no node found selector error during page already started to refresh/load
      // console.log(e);
    }

    const MAX_ATTEMPTS = 3;
    let attempt = 0;
    while ((attempt++) < MAX_ATTEMPTS) {
      currentURL = await this._page.url();
      if (currentURL.includes('/home')) {
        return true;
      }
      await this._solveChallenge(startLoginTS);
      await this._page.waitFor(3000);
    }
    // await this._page.waitFor(1500000);
    console.log("Max attempts value exceeded");
    await this._page.waitFor(15000);
    return false;
  }

  async run() {
    await super.run();
    if (this._credentials?.pop3_host && this._credentials?.pop3_port) {
      this._emailClient = new POP3Client(
        this._credentials?.email,
        this._credentials?.email_password,
        {
          host: this._credentials?.pop3_host,
          port: this._credentials?.pop3_port
        }
      )
    }
    /**
     * Go to homepage and auth.
     * remember login process start timestamp.
     */
    await this.goWithRetries('https://twitter.com');
    const startTS = await this._login();
    if (startTS === false) {
      throw Error("Failed to login");
    }

    return await this._page.cookies();
  };

  async _solveChallenge(startLoginTS) {
    let pageURL = await this._page.url();
    if (pageURL.includes('login_challenge')) {
      const challengeTypeElement = await this._page.$('input[name="challenge_type"]')
      if ((challengeTypeElement !== null)) {
        const challengeType = await (await challengeTypeElement.getProperty('value')).jsonValue();
        if (challengeType === 'RetypeEmail') {
          await this._page.type('input[id="challenge_response"]', this._credentials?.email, {delay: 80});
          await this._page.waitFor(2000);
          if (await this._page.$('input[id="email_challenge_submit"]') !== null) {
            await this._page.clickAndWaitForNavigation('input[id="email_challenge_submit"]');
          }
        } else if (challengeType === 'TemporaryPassword' && this._emailClient !== null) {
          const verificationCode = await this._emailClient.getVerificationCode(startLoginTS);
          console.log("Email verification code: ", verificationCode);
          await this._page.type('input[id="challenge_response"]', verificationCode, {delay: 80});
          await this._page.waitFor(2000);
          if (await this._page.$('input[id="email_challenge_submit"]') !== null) {
            await this._page.clickAndWaitForNavigation('input[id="email_challenge_submit"]');
          }
        }
      }
    }
    if (pageURL.includes('account/access')) {
      let googleRecaptchaLiElement = await this._page.evaluate(() => {
        let helpElement = (Array.from(document.querySelectorAll('li')) || []).find(
          el => el.textContent.includes('Google reCAPTCHA')
        );
        if (helpElement) {
          return helpElement.innerText;
        }
        return null;
      });
      // console.log(googleRecaptchaLiElement);
      if (googleRecaptchaLiElement !== null) {
        await this._page.clickAndWaitForNavigation('input[type="submit"]');
        if (await this._page.$('div[id="recaptcha_element"]') !== null) {
          await this._solveCaptcha();
        }
      }

      let areYouRobotElement = await this._page.evaluate(() => {
        let helpElement = (Array.from(document.querySelectorAll('div[class="PageHeader Edge"]')) || []).find(
          el => el.textContent.includes('a robot?')
        );
        if (helpElement) {
          return helpElement.innerText;
        }
        return null;
      });
      if (areYouRobotElement !== null) {
        await this._solveCaptcha();
      }

      let thanksHumanElement = await this._page.evaluate(() => {
        let helpElement = (Array.from(document.querySelectorAll('div[class="PageHeader Edge"]')) || []).find(
          el => el.textContent.includes('Thanks')
        );
        if (helpElement) {
          return helpElement.innerText;
        }
        return null;
      });
      if (thanksHumanElement !== null) {
        await this._page.clickAndWaitForNavigation('input[type="submit"]');
      }
    }
  }

  async _solveCaptcha() {
    const googleSiteKey = await this._page.evaluate(() => {
      let captchaIFrame = document.querySelector('div[id="recaptcha_element"] iframe');
      let url = new URL(captchaIFrame.src);
      let keyMatch =  url.search.match(/k=([A-Za-z0-9-_]+)&?/mi);
      if (keyMatch && keyMatch.length > 1) {
        return keyMatch[1];
      }
      return null;
    });
    const currentURL = await this._page.url();
    try {
      this._captchaToken = await this._ruCaptchaClient.getSolution(
        googleSiteKey,
        currentURL,
        this._credentials['proxies.username'],
        this._credentials['proxies.password'],
        `${this._credentials.host}:${this._credentials.port}`,
      );
    } catch (e) {
      if (e.message === 'ERROR_ZERO_BALANCE') {
        throw Error("Captcha Solver Service Account has zero balance");
      }
      throw Error("Failed to solve captcha restriction");
    }

    await this._page.evaluate((token) => {
      const inp = document.querySelector('textarea[id="g-recaptcha-response"]');
      inp.value = token;
      const verification = document.querySelector('input[id="verification_string"]');
      verification.value = token;
    }, this._captchaToken);
    await this._page.evaluate(() => {
      document.getElementById("continue_button").style.display = "block";
    });
    await this._page.clickAndWaitForNavigation('input[id="continue_button"]');
  }
}

module.exports = TwitterAuthSpider;
