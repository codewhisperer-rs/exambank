'use client'
import {InputBox} from "@/components/input-box/input-box";
import {ChatList} from "@/components/chat-list/chat-list";
import {useEffect, useRef} from "react";
import {useInputBoxStateStore} from "@/store/input-box-state-store";

export default function ChatPage() {
    const inputBoxRef = useRef(null)
    const inputBoxState=useInputBoxStateStore()
    useEffect(() => {
        inputBoxState.setInputBoxStateStore(prevState => ({...prevState,inputBoxRef}))
    }, []);
    return <>
        <div className={"w-full min-h-[95vh] h-fit relative flex flex-col items-center "}>
            <div className={"relative min-h-full grow max-w-4xl w-full px-4"}>
                <ChatList/>
            </div>
            <div className={"sticky h-fit bottom-0 pb-2 w-full flex flex-col items-center justify-center bg-blue-50"}>
                <div className={"max-w-4xl w-full h-fit rounded-md px-4"}>
                    <InputBox ref={inputBoxRef}/>
                </div>
            </div>
        </div>


    </>
}