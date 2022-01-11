import axios from "axios";

export default class WitAi {
    public static async speechAudio(mp3File: Buffer, accessKey: string, timeout: number = 30000): Promise<string> {
        try {
            const response = await axios.post('https://api.wit.ai/speech', mp3File, {
                headers: {
                    'Authorization': `Bearer ${accessKey}`,
                    'Content-Type': 'audio/mpeg',
                    'accept': 'application/vnd.wit.20200513+json' // pywit
                },
                timeout: timeout
            });
            return response.data.text;
        } catch (e) {
            //@ts-ignore
            const errorMessage = e.response.data?.error || e.toString();
            throw new Error(`wit.ai exception: ${errorMessage}`);
        }
    }
}
