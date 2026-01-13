import {zh_cn} from "@/locales/zh_cn";

export const en = {
    ...zh_cn,
    "page-header.title": "Aqua AI Chat",
    
    "input-box.input.placeholder": "What do you want to know?",
    "input-box.attachment.title": "Upload",
    "input-box.attachment.upload.label": "Attachment Upload",
    "input-box.attachment.upload.button": "Upload",
    "input-box.attachment.upload.message": "Drag here to upload",
    "input-box.attachment.upload.recent": "Recent",
    "chat-fragment.thinking.thinking-title": (startTime: number, finishTime: number, finished: boolean) => {
        if (finished) return `Thinking finished Time cost: ${Math.floor((finishTime - startTime) / 1000)} s`;
        else return `Thinking already cost ${Math.floor((startTime - Date.now()) / 1000)} s`
    },
    "chat-fragment.actions.copy": "Copy",
    "chat-fragment.actions.retry": "Retry",
    "chat-fragment.actions.good-feedback": "Like",
    "chat-fragment.actions.bad-feedback": "Dislike",
}