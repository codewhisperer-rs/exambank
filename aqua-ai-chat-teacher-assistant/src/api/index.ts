
import {ModelConfig} from "@/schema/model-config";
import {ChatSession} from "@/schema/chat-session";
import {DeepseekApi} from "@/api/deepseek-api";
import {SetStateAction} from "react";
import {FakeServerApi} from "@/api/fake-server-api";
import {GrokApi} from "@/api/grok-api";
export class ChatConfig{
    session: ChatSession | undefined
    onFinish?: () => void;
    messageIndex?:number;
}
export interface ChatApi {
    sendMessage:(config:ChatConfig,updater:(action:SetStateAction<ChatSession>)=>void)=>void
    stop:()=>void,
}
export function getApiByModelName(model:ModelConfig){
    // 无论选择什么模型，都返回GrokApi
    return new GrokApi();
}