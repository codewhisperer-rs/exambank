import {ChatApi, ChatConfig} from "@/api/index";
import React from "react";
import {ChatSession} from "@/schema/chat-session";
import {ChatMessage} from "@/schema/chat-message";
import {Thinking} from "@/schema/chat-message-metadata/thinking";

const responseMessageContent = ``
const responseThinkingContent = ``
const deltaTime = 4

export class FakeServerApi implements ChatApi {
    stopStream = false;

    sendMessage(config: ChatConfig, updater: (action: React.SetStateAction<ChatSession>) => void): void {
        const botMessage: ChatMessage = {
            role: "assistant",
            contents: [""],
            streaming: true,
            thinking: {startTime: Date.now(), content: "", finished: false} as Thinking
        }
        updater(prev => {
            return {
                ...prev,
                messages: [...prev.messages, botMessage],
                streaming: true,
            }
        })
        this.stopStream = false
        //这是一个假服务器用于测试 现在需要按delta每个字地返回responseMessageContent和responseThinkingContent
        botMessage.thinking = {startTime: Date.now(), content: "", finished: false} as Thinking
        for (let i = 0; i < responseThinkingContent.length; i++) {
            setTimeout(() => {
                if (this.stopStream) {
                    return
                }
                botMessage.thinking!.content += responseThinkingContent[i]
                updater(prev => {
                    return {
                        ...prev,
                        messages: prev.messages.concat()
                    }
                })
                if (i >= responseThinkingContent.length - 1) {
                    botMessage.thinking!.finishTime = Date.now()
                    botMessage.thinking!.finished = true
                }

            }, i * deltaTime)
        }
        botMessage.thinking!.finishTime = Date.now()
        botMessage.thinking!.finished = true
        for (let i = 0; i < responseMessageContent.length; i++) {
            setTimeout(() => {
                if (this.stopStream) {
                    return
                }
                botMessage.contents[0] += responseMessageContent[i]
                updater(prev => {
                    return {
                        ...prev,
                        messages: prev.messages.concat()
                    }
                })
            }, i * deltaTime + responseThinkingContent.length * deltaTime)
        }
        botMessage.streaming = false
        config.onFinish?.()
    }

    stop(): void {
        this.stopStream = true;
    }

}