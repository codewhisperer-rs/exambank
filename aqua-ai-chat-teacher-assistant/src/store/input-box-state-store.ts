import {RefObject, SetStateAction} from "react";
import {create} from "zustand/react";
import {applySetStateAction} from "@/utils";

interface InputBoxStateStore {
    chat: ((index?: number) => void) | undefined,
    setInputBoxStateStore: (state: SetStateAction<Partial<InputBoxStateStore>>) => void
    inputBoxRef: RefObject<any> | undefined
}

export const useInputBoxStateStore = create<InputBoxStateStore>((set, get) => ({
    chat: undefined,
    setInputBoxStateStore: (state) => {
        const data = get()
        set({...data, ...applySetStateAction(data, state)})
    },
    inputBoxRef: undefined
}))