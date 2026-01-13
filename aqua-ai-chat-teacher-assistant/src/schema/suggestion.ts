import {z} from "zod"

export const SuggestionSchema = z.object({
    name: z.string(),
    content: z.string()
})
export type Suggestion = z.infer<typeof SuggestionSchema>
export const defaultSuggestions: Suggestion[] = [
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "Rust中可变借用和不可变借用的区别"
    },
    {
        name: "编程助手",
        content: "使用Kotlin写一段简单的Http服务器代码"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
    {
        name: "编程助手",
        content: "给我写一段JavaScript的数组快速排序"
    },
]