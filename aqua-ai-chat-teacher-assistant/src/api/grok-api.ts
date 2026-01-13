'use client'
import {ChatApi, ChatConfig} from "@/api/index";
import {SetStateAction} from "react";
import {ChatSession} from "@/schema/chat-session";
import {ChatMessage} from "@/schema/chat-message";
import {Thinking} from "@/schema/chat-message-metadata/thinking";

export class GrokApi implements ChatApi {
    stopStream = false;
    private API_URL = 'https://api.deepseek.com/chat/completions';
    // 直接在代码中设置API密钥
    private API_KEY: string = "";

    constructor(apiKey?: string) {
        // 如果提供了apiKey参数，则使用它覆盖硬编码的密钥
        if (apiKey) {
            this.API_KEY = apiKey;
        }
    }

    // 设置API密钥方法
    setApiKey(apiKey: string) {
        this.API_KEY = apiKey;
    }

    async sendMessage(config: ChatConfig, updater: (action: SetStateAction<ChatSession>) => void) {
        const botMessage: ChatMessage = {
            role: "assistant",
            contents: [""],
            streaming: true,
            thinking: {startTime: Date.now(), content: "", finished: false} as Thinking
        }
        
        updater(prev => ({
            ...prev,
            messages: [...prev.messages, botMessage],
            streaming: true,
        }));
        
        this.stopStream = false;
        
        if (!config.session) {
            botMessage.streaming = false;
            botMessage.contents[0] = "会话不存在";
            updater(prev => ({
                ...prev,
                streaming: false,
                messages: prev.messages.concat()
            }));
            return;
        }

        try {
            // 准备消息历史，添加系统角色提示
            const systemMessage = {
                role: "system",
                content: "你是一个知识面广的计算机专业助教，擅长解答各种计算机科学领域的问题，包括但不限于编程语言、算法、数据结构、计算机网络、操作系统、计算机组成原理、人工智能等。你的回答应该专业、准确、简洁明了，且富有教育意义。"
            };
            
            const messages = [
                systemMessage,
                ...config.session.messages.map(msg => ({
                    role: msg.role,
                    content: msg.contents[0]
                }))
            ];
            
            // 记录思考内容
            const lastUserMessage = config.messageIndex 
                ? config.session.messages[config.messageIndex] 
                : config.session.messages[config.session.messages.length - 1];
                
            botMessage.thinking!.content = `用户: ${lastUserMessage.contents[0]}`;
            
            // 调用API进行流式响应
            const response = await fetch(this.API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.API_KEY}`
                },
                body: JSON.stringify({
                    model: 'deepseek-chat', 
                    messages: messages,
                    stream: true,
                    temperature: 0.7,
                    max_tokens: 2000
                })
            });
            
            if (!response.ok) {
                throw new Error(`API调用失败: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error("无法获取响应流");
            }

            const decoder = new TextDecoder();
            let content = '';

            while (true) {
                if (this.stopStream) {
                    break;
                }

                const { done, value } = await reader.read();
                if (done) {
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim() !== '');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;

                        try {
                            const parsed = JSON.parse(data);
                            const delta = parsed.choices[0]?.delta?.content || '';
                            if (delta) {
                                content += delta;
                                botMessage.contents[0] = content;
                                
                                updater(prev => ({
                                    ...prev,
                                    messages: prev.messages.concat()
                                }));
                            }
                        } catch (e) {
                            console.error('解析事件数据错误:', e);
                        }
                    }
                }
            }

            // 完成流式响应
            botMessage.streaming = false;
            botMessage.thinking!.finished = true;
            botMessage.thinking!.finishTime = Date.now();

            updater(prev => ({
                ...prev,
                streaming: false,
                messages: prev.messages.concat()
            }));

            config.onFinish?.();
        } catch (error) {
            console.error('Groq API调用错误:', error);
            botMessage.streaming = false;
            botMessage.contents[0] = `API调用失败: ${error instanceof Error ? error.message : '未知错误'}`;
            
            updater(prev => ({
                ...prev,
                streaming: false,
                messages: prev.messages.concat()
            }));
            
            botMessage.thinking!.finished = true;
            botMessage.thinking!.finishTime = Date.now();
            config.onFinish?.();
        }
    }

    stop(): void {
        this.stopStream = true;
    }
} 