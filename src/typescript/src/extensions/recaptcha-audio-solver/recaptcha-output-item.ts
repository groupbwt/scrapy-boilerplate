import InputItem from "../../items/input-item/input-item";

export default class RecaptchaOutputItem extends InputItem {
    constructor(
        public g_recaptcha_response: string
    ) {
        super();
    }
}
