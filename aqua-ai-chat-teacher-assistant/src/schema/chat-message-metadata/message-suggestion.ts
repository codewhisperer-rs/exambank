import {z} from "zod"
import {ChatMessageSchema} from "@/schema/chat-message";

export const MessageSuggestionSchema = z.object({
    suggestions: z.array(z.object({
        title: z.string(),
        description: z.string(),
        message: z.string()
    }))

})

export type MessageSuggestion = z.infer<typeof MessageSuggestionSchema>
