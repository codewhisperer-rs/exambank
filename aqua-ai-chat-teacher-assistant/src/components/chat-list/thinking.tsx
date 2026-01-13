import {ChatMessage} from "@/schema/chat-message";
import {Accordion, AccordionContent, AccordionItem, AccordionTrigger} from "@/components/ui/accordion";
import Markdown from "react-markdown";
import {motion} from "framer-motion";
import React from "react";
import {cn} from "@/lib/utils";
import {useLanguageStore} from "@/store/language-store";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {MarkdownViewer} from "@/components/MarkdownViewer";
export interface ThinkingProps {
    message: ChatMessage;
}

export function Thinking(props: ThinkingProps) {
    const language = useLanguageStore().language
    return <div className={"w-fit max-w-full"}>
        <Accordion type={"single"} className={"w-full"} collapsible defaultValue={"item-1"}>
            
            <AccordionItem value={"item-1"} >
                <AccordionTrigger className={" w-full select-none hover:no-underline justify-start"}>
                    <span
                        className={cn("select-none text-foreground/60 font-semibold hover:text-foreground/80 transition hover:cursor-pointer")}>
                        {language["chat-fragment.thinking.thinking-title"](props.message.thinking?.startTime || Date.now(), props.message.thinking?.finishTime || Date.now(), props.message.thinking?.finished || true)}
                    </span>
                    
                </AccordionTrigger>
                <AccordionContent className={"border-x-2 border-foreground/20 px-3 py-3 break-words "}>
                    <motion.div
                        initial={{height: 0, opacity: 0}}
                        animate={{height: "auto", opacity: 1}}
                        exit={{height: 0, opacity: 0}}
                        transition={{duration: 0.3}}
                        className={"break-words"}
                    >
                        <MarkdownViewer content={props.message.thinking!.content}></MarkdownViewer>
                    </motion.div>
                </AccordionContent>

            </AccordionItem>
        </Accordion>

    </div>
}