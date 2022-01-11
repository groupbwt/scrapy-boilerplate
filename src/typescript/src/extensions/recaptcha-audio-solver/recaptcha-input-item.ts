import InputItem from "../../items/input-item/input-item";

export default class RecaptchaInputItem extends InputItem {
    constructor(
        public url: string,
        public sitekey: string
    ) {
        super();
    }
}
