import {z} from "zod";
import {ThinkingSchema} from "@/schema/chat-message-metadata/thinking";
import {MessageSuggestionSchema} from "@/schema/chat-message-metadata/message-suggestion";

export const ChatMessageContentSchema = z.string().or(z.any())
export const ChatMessageSchema = z.object({
    contents: z.array(ChatMessageContentSchema),
    role: z.enum(["user", "assistant", "system"]),
    streaming: z.boolean(),
    thinking: ThinkingSchema.nullable().optional(),
    suggestion: MessageSuggestionSchema.nullable().optional(),
    metaType:z.enum(["greeting"]).optional().nullable(),
})
export type ChatMessageContent = z.infer<typeof ChatMessageContentSchema>
export type ChatMessage = z.infer<typeof ChatMessageSchema>
export const defaultUserMessage: ChatMessage = {
    contents: [""],
    role: "user",
    streaming: false
}
export const defaultGreetingMessage: ChatMessage = {
    contents: ["你好，我是你的助手，有什么可以帮助你的吗?"],
    role: "assistant",
    streaming: false,
    metaType: "greeting",
    suggestion: {
        suggestions: [{
            title: "自我介绍",
            description: "做一个简短的自我介绍",
            message: "请简短地介绍一下你自己",
        }]
    }
}