import React from "react";
import {HoverCard, HoverCardContent, HoverCardTrigger} from "@/components/ui/hover-card";

export interface ChatFragmentActionProps {
    trigger: React.ReactNode
    hover?: React.ReactNode
}

export function ChatFragmentAction(props: ChatFragmentActionProps) {
    return <HoverCard>
        <HoverCardTrigger>
            {props.trigger}
        </HoverCardTrigger>
        <HoverCardContent className={"max-w-32 w-fit flex items-center justify-center px-4 py-2 text-sm font-semibold text-foreground/70"}>
            {props.hover}
        </HoverCardContent>
    </HoverCard>
}