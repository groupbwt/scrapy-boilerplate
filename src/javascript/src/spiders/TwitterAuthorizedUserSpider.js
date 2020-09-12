import cloneDeep from "clone-deep";
import Apify from "apify";
import pauseFor from "../utils/pause";
import RabbitMQRPCServerWorker from "../rmq/RabbitMQRPCServerWorker";
import TwitterBaseSpider from "./TwitterBaseSpider";

const {puppeteer} = Apify.utils;


class TwitterAuthorizedUserSpider extends TwitterBaseSpider {

  constructor(authContext, config) {
    super(config?.headless || false, config?.ruCaptchaKey || null, {
      host: authContext['host'],
      port: authContext['port'],
      username: authContext['proxies.username'],
      password: authContext['proxies.password']
    })
    this._isInitCompleted = false;

    this._authContext = authContext;
    this._headless = config?.headless || false;
    this._rpcWorker = null;
    this._manageWorker = null;
    this._config = config;
    this._currentSessionID = null;
    this._currentSessionIDShouldStop = false;
  };

  async _login() {
    const startLoginTimestamp = Math.floor(Date.now() / 1000);
    for (const cookie of JSON.parse(this._authContext.cookies)) {
      await this._page.setCookie(cookie);
    }
    await this.goWithRetries('https://twitter.com/', 2);
    return startLoginTimestamp;
  }

  async run() {
    await super.run();
    /**
     * Go to homepage and auth.
     * remember login process start timestamp.
     */
    await this.goWithRetries('https://twitter.com');
    const startTS = await this._login();

    let currentURL = await this._page.url();
    if (currentURL.includes('/home') || (await this._page.$('a[href="/login"]') === null)) {
      if (this._rpcWorker === null) {
        this._rpcWorker = new RabbitMQRPCServerWorker(
          this._config.rmqConnectionURL,
          this._config.fullVersionTasksQueue,
        );
        await this._rpcWorker.connect(this.onTaskReceived.bind(this));
      }
      if (this._manageWorker === null) {
        this._manageWorker = new RabbitMQRPCServerWorker(
          this._config.rmqConnectionURL,
          this._config.manageTasksQueue,
        );
        await this._manageWorker.connect(this.onManageTaskReceived.bind(this));
      }
      for (; ;) {
        await pauseFor(10 * 1000);
      }
    } else {
      throw Error('failed to auth user')
    }
  };

  async onManageTaskReceived(msg) {
    const msgContent = JSON.parse(msg.content);
    try {
      if ((this._currentSessionID === null) || (msgContent?.id !== this._currentSessionID)) {
        await this._manageWorker.sendMessage(JSON.stringify(msgContent), this._config.manageTasksQueue);
      } else {
        this._currentSessionIDShouldStop = true;
      }
    } catch (e) {
      console.error(e);
    }
    await this._manageWorker._channel.ack(msg);
  }

  async onTaskReceived(msg) {
    const msgContent = JSON.parse(msg.content);
    let status = 4;
    let exception = "Failed to process";
    try {
      this._currentSessionID = msgContent?.session?.id;
      if (this._currentSessionIDShouldStop === true) {
        await this._sendReply(msg, msgContent, 23, null);
        this._currentSessionID = null;
        this._currentSessionIDShouldStop = false;
        return;
      }
      let targetPromise = null;
      if (msgContent?.module === 'retrieve_likes') {
        targetPromise = this._page.waitForResponse(response => response.url().includes('timeline/favorites'));
        await this.goWithRetries(`https://twitter.com/${msgContent?.profile.username}/likes`);
        let currentURL = await this._page.url();
        if (!currentURL.includes('/likes')) {
          throw Error('Likes Page was not reached');
        }
      } else if (msgContent?.module === 'retrieve_re_tweets') {
        targetPromise = this._page.waitForResponse(response => response.url().includes('timeline/profile'));
        await this.goWithRetries(`https://twitter.com/${msgContent?.profile.username}`);
        let currentURL = await this._page.url();
        if (!currentURL.includes(`/${msgContent?.profile.username}`)) {
          throw Error('Profile Page was not reached');
        }
      } else {
        throw Error(`Can not process module: ${msgContent?.module}`);
      }
      let resultData = [];
      let data = [];
      if (msgContent?.module === 'retrieve_likes') {
        data = await this.getNextPageLikesData(targetPromise, true);
      } else if (msgContent?.module === 'retrieve_re_tweets') {
        data = await this.getNextPageReTweetsData(targetPromise, true);
      }
      resultData.push(...(data?.entities || []));
      let shouldStop = false;
      let deltaZeroStreak = 0;
      const MAX_DELTA_ZERO_STREAK = 8;
      while ((resultData.length < msgContent?.max_results) && (shouldStop === false)) {
        if (this._currentSessionIDShouldStop === true) {
          status = 23;
          exception = null;
          this._currentSessionIDShouldStop = false;
          break;
        }
        if (msgContent?.module === 'retrieve_likes') {
          data = await this.getNextPageLikesData(null, false);
        } else if (msgContent?.module === 'retrieve_re_tweets') {
          data = await this.getNextPageReTweetsData(null, false);
        }
        shouldStop = data?.shouldStop;
        let prevResultDataLength = resultData.length;
        resultData.push(...(data?.entities || []));
        let delta = resultData.length - prevResultDataLength;
        deltaZeroStreak = (delta === 0) ? deltaZeroStreak + 1 : 0;
        if (shouldStop || (deltaZeroStreak >= MAX_DELTA_ZERO_STREAK)) {
          break;
        }
      }
      resultData = resultData.slice(0, msgContent?.max_results);
      await this._rpcWorker._channel.assertQueue(this._config.fullVersionResultsQueue, {durable: true});
      for (let resultDataItem of resultData) {
        await this._rpcWorker.sendMessage(
          {
            ...{
              module: msgContent?.module,
              profile_id: msgContent?.profile?.id,
              session_id: msgContent?.session?.id,
            },
            ...resultDataItem,
          },
          this._config.fullVersionResultsQueue,
        );
      }
      console.log('finish: ', resultData.length);

      if (status !== 23) {
        status = 2;
      }
      exception = null;
    } catch (e) {
      status = 4;
      exception = e.toString();
    }
    await this._sendReply(msg, msgContent, status, exception);
    this._currentSessionID = null;
  }

  async _sendReply(msg, msgContent, status, exception) {
    await this._rpcWorker._channel.assertQueue(msg.properties?.replyTo || this._config.fullVersionRepliesQueue, {durable: true});
    try {
      let response = cloneDeep(msgContent);
      response['status'] = status;
      response['exception'] = exception;
      await this._rpcWorker.sendMessage(response, msg.properties?.replyTo || this._config.fullVersionRepliesQueue);
      await this._rpcWorker._channel.ack(msg);
    } catch (e) {
      console.error(e);
      await this._rpcWorker._channel.ack(msg);
    }
  }

  async getNextPageLikesData(preparedPromise = null, isFirstResponse = false) {
    const promises = [];
    if (isFirstResponse) {
      promises.push(preparedPromise);
    } else {
      // promises.push(puppeteer.infiniteScroll(this._page, {timeoutSecs: 0, waitForSecs: 0, scrollDownAndUp: true}));
      promises.push(this._scrollToBottomOnce());
      promises.push(this._page.waitForResponse(response => response.url().includes('timeline/favorites'), {
        timeout: 5000
      }));
    }
    let results = await Promise.allSettled(promises);
    let shouldStop = false;
    let likes = [];
    for (let result of results) {
      if (result.status === "fulfilled" && result.value) {
        try {
          let responseJSON = await result.value.json();
          if (result.value.url().includes('timeline/favorites')) {
            if (Object.keys(responseJSON?.globalObjects?.tweets || []).length === 0) {
              shouldStop = true;
              break;
            }
            likes.push(...await this._extractLikesData(responseJSON));
          }
        } catch (e) {
          console.log(e);
        }
      }
    }
    return {
      shouldStop: shouldStop,
      entities: likes
    }
  }

  async getNextPageReTweetsData(preparedPromise = null, isFirstResponse = false) {
    const promises = [];
    if (isFirstResponse) {
      promises.push(preparedPromise);
    } else {
      // promises.push(puppeteer.infiniteScroll(this._page, {timeoutSecs: 0, waitForSecs: 0, scrollDownAndUp: false}));
      promises.push(this._scrollToBottomOnce());
      promises.push(this._page.waitForResponse(response => response.url().includes('timeline/profile'), {
        timeout: 5000
      }));
    }
    let results = await Promise.allSettled(promises);
    let shouldStop = false;
    let reTweets = [];
    for (let result of results) {
      if (result.status === "fulfilled" && result.value) {
        try {
          let responseJSON = await result.value.json();
          if (result.value.url().includes('timeline/profile')) {
            if (Object.keys(responseJSON?.globalObjects?.tweets || []).length === 0) {
              shouldStop = true;
              break;
            }
            reTweets.push(...await this._extractReTweetsData(responseJSON));
          }
        } catch (e) {
          console.log(e);
        }
      }
    }
    return {
      shouldStop: shouldStop,
      entities: reTweets
    }
  }

  async _extractLikesData(likesResponseJSON) {
    let likesData = [];
    for (let tweetID in likesResponseJSON?.globalObjects?.tweets) {
      if (likesResponseJSON?.globalObjects?.tweets.hasOwnProperty(tweetID)) {
        let tweet = likesResponseJSON?.globalObjects?.tweets[tweetID]
        let tweetAuthor = likesResponseJSON?.globalObjects?.users[tweet?.user_id_str];
        likesData.push({
          tweet_author_id: tweet?.user_id_str,
          tweet_author_username: tweetAuthor?.screen_name,
          tweet_author_full_name: tweetAuthor?.name,
          tweet_author_is_verified: tweetAuthor?.verified,
          tweet_id: tweet?.id_str,
          tweet_text: tweet?.full_text,
          tweet_relative_permalink: `/${tweetAuthor?.screen_name}/status/${tweet?.id_str}`,
          tweet_created_date: tweet?.created_at,
          tweet_re_tweets_count: tweet?.retweet_count,
          tweet_likes_count: tweet?.favorite_count,
        })
      }
    }
    return likesData;
  }

  async _extractReTweetsData(profileResponseJSON) {
    let reTweetsData = [];
    for (let tweetID in profileResponseJSON?.globalObjects?.tweets) {
      if (profileResponseJSON?.globalObjects?.tweets.hasOwnProperty(tweetID)) {
        let tweet = profileResponseJSON?.globalObjects?.tweets[tweetID]
        let tweetAuthor = profileResponseJSON?.globalObjects?.users[tweet?.user_id_str];
        if (tweet.hasOwnProperty('retweeted_status_id_str')) {
          let refTweet = profileResponseJSON?.globalObjects?.tweets[tweet?.retweeted_status_id_str];
          let refTweetAuthor = profileResponseJSON?.globalObjects?.users[refTweet?.user_id_str];
          reTweetsData.push({
            tweet_author_id: tweet?.user_id_str,
            tweet_author_username: tweetAuthor?.screen_name,
            tweet_author_full_name: tweetAuthor?.name,
            tweet_author_is_verified: tweetAuthor?.verified,
            tweet_id: tweet?.id_str,
            tweet_text: tweet?.full_text,
            tweet_relative_permalink: `/${tweetAuthor?.screen_name}/status/${tweet?.id_str}`,
            tweet_created_date: tweet?.created_at,
            tweet_re_tweets_count: tweet?.retweet_count,
            tweet_likes_count: tweet?.favorite_count,

            ref_tweet_author_id: refTweet?.user_id_str,
            ref_tweet_author_username: refTweetAuthor?.screen_name,
            ref_tweet_author_full_name: refTweetAuthor?.name,
            ref_tweet_author_is_verified: refTweetAuthor?.verified,
            ref_tweet_id: tweet?.retweeted_status_id_str,
            ref_tweet_text: refTweet?.full_text,
            ref_tweet_relative_permalink: `/${refTweetAuthor?.screen_name}/status/${refTweet?.id_str}`,
            ref_tweet_created_date: refTweet?.created_at,
            ref_tweet_re_tweets_count: refTweet?.retweet_count,
            ref_tweet_likes_count: refTweet?.favorite_count,
          })
        }
      }
    }
    return reTweetsData;
  }

  async _stepScrollToBottomOnce() {
    const bodyHeight = await this._page.evaluate(() => document.body.clientHeight);
    const stepSize = 300;
    // const stepSize = 100;
    for (let step = 0; step < Math.ceil(bodyHeight / stepSize); step += 1) {
      let scrollYPosition = (step + 1) * stepSize;
      await this._page.evaluate((scrollYPosition) => {
        window.scrollTo(0, scrollYPosition);
      }, scrollYPosition);
      await this._page.waitFor(Math.floor(Math.random() * (250 - 100)) + 100);
    }
  }

  async _scrollToBottomOnce() {
    const SCROLL_HEIGHT_IF_ZERO = 10000;
    await this._page.evaluate((scrollHeightIfZero) => {
      const delta = document.body.scrollHeight === 0 ? scrollHeightIfZero : document.body.scrollHeight;
      window.scrollBy(0, delta);
    }, SCROLL_HEIGHT_IF_ZERO);
  }
}

module.exports = TwitterAuthorizedUserSpider;
