'use client'
import {useInputStore} from "@/store/input-store";
import {Textarea} from "@/components/ui/textarea";
import {AttachmentUploader} from "@/components/input-box/attachment-uploader";
import {Button} from "@/components/ui/button";
import {useLanguageStore} from "@/store/language-store";
import {ModelSelector} from "@/components/input-box/model-selector";
import {Suggestions} from "@/components/input-box/suggesions";
import {forwardRef, useEffect, useImperativeHandle, useRef, useState} from "react";
import {useChatStore} from "@/store/chat-store";
import {ChatApi, ChatConfig, getApiByModelName} from "@/api";
import {useChatListStateStore} from "@/store/chat-list-state-store";
import {ChevronDown, SendIcon, SquareIcon} from "lucide-react";
import {ChatMessage} from "@/schema/chat-message";
import {useInputBoxStateStore} from "@/store/input-box-state-store";


export const InputBox = forwardRef((props, ref) => {
    const inputStore = useInputStore();
    const languageStore = useLanguageStore()
    const chatStore = useChatStore()
    const [focus, setFocus] = useState(false);
    const divRef = useRef<HTMLDivElement>(null);
    const isComposingRef = useRef(false);
    const chatApiRef = useRef<ChatApi | null>(null)
    const chatListStateStore = useChatListStateStore();
    const inputBoxStateStore = useInputBoxStateStore();
    useEffect(() => {
        const handleFocusIn = () => setFocus(true);
        const handleFocusOut = () => {
            // 如果正在进行输入法组合输入，则不修改 focus 状态

            setTimeout(() => {

                if (isComposingRef.current) return;
                setFocus(false);
            }, 0)

        };

        const handleCompositionStart = () => {
            isComposingRef.current = true;
        };

        const handleCompositionEnd = () => {
            isComposingRef.current = false;
        };

        const div = divRef.current;
        if (div) {
            div.addEventListener("focusin", handleFocusIn);
            div.addEventListener("focusout", handleFocusOut);
            div.addEventListener("compositionstart", handleCompositionStart);
            div.addEventListener("compositionend", handleCompositionEnd);
        }

        return () => {
            if (div) {
                div.removeEventListener("focusin", handleFocusIn);
                div.removeEventListener("focusout", handleFocusOut);
                div.removeEventListener("compositionstart", handleCompositionStart);
                div.removeEventListener("compositionend", handleCompositionEnd);
            }
        };
    }, []);
    const chat = (message?: ChatMessage) => {
        if (chatStore.getCurrentSession().streaming) {
            chatStore.updateCurrentSession(prev => {
                return {
                    ...prev,
                    streaming: false
                }
            })
            if (!chatApiRef.current) {
                return
            }
            chatApiRef.current.stop()
        } else {
            chatListStateStore.setAutoScroll(true)

            const addScrollListener = () => {
                let lastScrollTop = window.scrollY;
                const scrollListener = function () {
                    let currentScrollTop = window.scrollY;
                    //console.log(currentScrollTop, lastScrollTop)
                    if (currentScrollTop < lastScrollTop) {
                        chatListStateStore.setAutoScroll(false)
                        window.removeEventListener("scroll", scrollListener)

                    } else if (currentScrollTop > lastScrollTop) {
                    }
                    lastScrollTop = currentScrollTop; // 更新上一次滚动位置
                }
                window.addEventListener("scroll", scrollListener)
            }
            addScrollListener()
            const model = chatStore.getCurrentSession().modelConfig
            const api = getApiByModelName(model)

            let userMessage = {
                role: "user",
                contents: [inputStore.content],
            } as ChatMessage
            if (message) {
                userMessage = message
            } else {
                inputStore.setContent("")
            }
            chatStore.updateCurrentSession(prev => {
                return {...prev, messages: [...prev.messages, userMessage]}
            })
            if (!api) return
            else {
                chatApiRef.current = api as ChatApi
                const config: ChatConfig = {
                    session: chatStore.getCurrentSession(),
                    onFinish: () => {
                        chatListStateStore.setAutoScroll(false)
                    },
                }
                api.sendMessage(config, chatStore.updateCurrentSession)

            }
        }
    }
    useImperativeHandle(ref, () => ({
        chat: chat
    }));
    return <div
        ref={divRef}
        className="transition-all relative w-full min-h-28 h-fit max-h-[60vh] border-[1px] border-foreground/10 rounded-2xl bg-background flex flex-col py-2 px-2 ">
        {!chatListStateStore.isAtBottom &&
            <Button variant={"outline"} className={"w-10 h-10 rounded-full absolute -top-11 -right-0 "} onClick={() => {
                chatListStateStore.scrollToBottom()
            }}><ChevronDown/> </Button>}

        {false&&<Suggestions open={focus}/>}

        <Textarea
            placeholder={languageStore.language["input-box.input.placeholder"]}
            className={"w-full max-h-40 grow resize-none bg-transparent border-none shadow-none overflow-y-auto outline-0 focus:outline-0 focus:ring-0 focus:border-0 focus-visible:ring-0 focus-visible:border-none"}
            onChange={e => {
                inputStore.setContent(e.target.value)
            }} value={inputStore.content}/>
        <div className={"min-h-12 flex flex-row items-center px-2 gap-2"}>
            {false&&<AttachmentUploader/>}
            <div className={"grow"}/>
            {false&&<ModelSelector/>}
            <Button onClick={() => {
                chat()
            }} className={"rounded-full h-7 w-7 sm:h-10 sm:w-10 hover:cursor-pointer"}
                    disabled={(!chatStore.getCurrentSession().streaming) && inputStore.isEmpty()}>
                {chatStore.getCurrentSession().streaming ? <SquareIcon/> : <SendIcon/>}
            </Button>
        </div>
    </div>


})