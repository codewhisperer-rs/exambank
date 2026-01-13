'use client'
import {ChatApi, ChatConfig} from "@/api/index";
import {SetStateAction} from "react";
import {ChatSession} from "@/schema/chat-session";
import {ChatMessage} from "@/schema/chat-message";
import {Thinking} from "@/schema/chat-message-metadata/thinking";


export class DeepseekApi implements ChatApi {
    stopStream = false;

    sendMessage(config: ChatConfig, updater: (action: SetStateAction<ChatSession>) => void) {
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
        const userMessage = config.session?.messages[config.session?.messages.length - 1]
        let i = 0
        let it = 0
        updater(prev => {
            return {
                ...prev,
                messages: prev.messages.concat()
            }
        })
        let lastMessage = config.session?.messages[config.session?.messages.length - 1]
        if (config.messageIndex) {

            lastMessage = config.session?.messages[config.messageIndex]
        }
        //console.log(lastMessage)
        botMessage.thinking!.content += lastMessage.contents[0]
        botMessage.thinking!.finished = false
       botMessage.thinking!.finishTime = Date.now()
        const inter = setInterval(() => {
            botMessage.contents[0] += i

            updater(prev => {
                return {
                    ...prev,
                    messages: prev.messages.concat()
                }
            })
            i++
            if (i > 300) {
                botMessage.streaming = false
                config.onFinish?.()
                clearInterval(inter)
                updater(prev => {
                    return {
                        ...prev,
                        streaming: false,
                        messages: prev.messages.concat()
                    }
                })
            }
            if (this.stopStream) {
                botMessage.streaming = false
                config.onFinish?.()
                clearInterval(inter)
                updater(prev => {
                    return {
                        ...prev,
                        streaming: false,
                        messages: prev.messages.concat()
                    }
                })
            }
        }, 20)

    }

    stop(): void {
        this.stopStream = true
    }
}