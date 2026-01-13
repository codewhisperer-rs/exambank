import {ChatMessage, defaultUserMessage} from "@/schema/chat-message";
import {useLanguageStore} from "@/store/language-store";
import {useInputBoxStateStore} from "@/store/input-box-state-store";
import {useChatStore} from "@/store/chat-store";

export interface SuggestionProps {
    message: ChatMessage

}

export function Suggestion({message}: SuggestionProps) {
    const language = useLanguageStore().language
    const inputBoxState = useInputBoxStateStore()
    const streaming=useChatStore(state => {return state.sessions[state.currentSessionIndex].streaming})
    return (
        <div className={"w-full h-fit"}>
            <h1 className={"font-black text-foreground/80 font-mono"}>{language['chat-fragment.suggestion.suggestion-title']}</h1>
            <div className={"w-full h-fit"}>
                {message.suggestion?.suggestions.map((it, index) => {
                    return <div onClick={() => {
                        if (streaming) return
                        const newMessage = defaultUserMessage
                        newMessage.contents = [it.message]
                        console.log(1)
                        inputBoxState?.inputBoxRef?.current?.chat?.(newMessage)

                    }} key={index}
                                className={"w-full h-fit border-[1px] rounded-md px-3 py-3 my-2 flex flex-col gap-2 " + ((!streaming)&&" hover:cursor-pointer hover:bg-foreground/10")}>
                        <h1 className={"font-black text-foreground/80 font-mono"}>{it.title}</h1>
                        <div className={"w-full h-fit"}>
                            {it.description}
                        </div>
                    </div>
                })}
            </div>
        </div>
    )
}