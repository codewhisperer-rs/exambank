'use client'
import {Button} from "@/components/ui/button";
import {useChatStore} from "@/store/chat-store";
import {defaultChatSession} from "@/schema/chat-session";
import {SessionSelector} from "@/components/session-selector";
import {useLanguageStore} from "@/store/language-store";

export function PageHeader() {
    const chatStore = useChatStore()
    const language=useLanguageStore()
    
    return <div
        className={"w-full h-12 sticky top-0 left-0 bg-gradient-to-b from-blue-50 via-blue-50 via-80% to-transparent z-40"}>
        <div className={"w-full h-full flex flex-row items-center px-4"}>
            <Button className={"h-2/3 hidden sm:block"} variant={"link"} onClick={() => {
                chatStore.setChatStore(prev => {
                    return {
                        ...prev,
                        sessions: prev.sessions?.concat(defaultChatSession),
                        currentSessionIndex: prev.sessions?.length,
                    }
                })
            }}>{chatStore.getCurrentSession().name||language.language["page-header.title"]}</Button>
            <div className={"grow"}/>
            <SessionSelector/>
        </div>
    </div>
}