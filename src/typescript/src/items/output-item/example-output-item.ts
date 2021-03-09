import OutputItem from "./output-item";

export default class ExampleOutputItem extends OutputItem {
    constructor(
        public url: string,
        public status: number,
    ) {
        super();
    }
}
