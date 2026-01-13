'use client'
import {create} from "zustand/react";
import {SetStateAction} from "react";
import {applySetStateAction} from "@/utils";

interface ChatListState {
    chatListElement?: HTMLDivElement;
    setChatListElement: (action: SetStateAction<HTMLDivElement | undefined>) => void;
    scrollToBottom: () => void,
    isAtBottom: boolean,
    setAtBottom: (value: boolean) => void,
    scrollToBottomWithClientHeight: () => void,
    autoScroll: boolean,
    setAutoScroll: (value: boolean) => void,
    renderMessageIndex: number,
    setRenderMessageIndex: (value: number) => void,
}

export const useChatListStateStore = create<ChatListState>((set, get) => ({

    chatListElement: undefined,
    setChatListElement: (action) => {
        set(prev => {
            return {...prev, chatListElement: applySetStateAction(get().chatListElement, action)};
        });
    },
    scrollToBottom: () => {
        //console.log(document.body.scrollHeight)
        window.scrollTo({top: document.body.scrollHeight, behavior: "auto"});
    },
    isAtBottom: true,
    setAtBottom: (value) => {
        set(prev => ({...prev, isAtBottom: value}))
    },
    scrollToBottomWithClientHeight: () => {
    },
    autoScroll: false,
    setAutoScroll: (value: boolean) => {
        set(prev => ({...prev, autoScroll: value}));
    },
    renderMessageIndex: 0,
    setRenderMessageIndex: (v: number) => set(prev => ({...prev, renderMessageIndex: v}))
}))
