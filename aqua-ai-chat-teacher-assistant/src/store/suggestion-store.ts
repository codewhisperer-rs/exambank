import {create} from "zustand/react";
import {defaultSuggestions, Suggestion} from "@/schema/suggestion";
import {SetStateAction} from "react";
import {applySetStateAction} from "@/utils";

interface SuggestionStore {
    suggestions: Suggestion[],
    setSuggestions: (action: SetStateAction<Suggestion[]>) => void
}

export const useSuggestionStore = create<SuggestionStore>((set, get) => ({
    suggestions: defaultSuggestions,
    setSuggestions: (action) => {
        const {suggestions} = get()
        set({...get(), suggestions: applySetStateAction(suggestions, action)})
    }
}))