'use client'
import {SetStateAction} from "react";

export function applySetStateAction<T>(prev: T, action: SetStateAction<T>): T {
    let value = prev
    if (typeof action === "function") {
        value = (action as ((prevState: T) => T))(prev)
    } else {
        value = action
    }
    return value
}