import {z} from "zod";

export const models = [
    {
        name: "deepseek-chat"
        //name: "grok-3-mini-beta"
    }
]
export const ModelConfigSchema = z.object({
    name: z.string()
})
export type ModelConfig=z.infer<typeof ModelConfigSchema>
export const defaultModelConfig = models[0]