import Imap = require('imap')
import {Socket} from "net";


export default interface ImapClientConfig extends Imap.Config {
    socket?: Socket
}
