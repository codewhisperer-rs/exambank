'use client'

import {useEffect, useState} from "react";
import {DropdownMenu, DropdownMenuContent, DropdownMenuTrigger} from "@/components/ui/dropdown-menu";
import {Button} from "@/components/ui/button";
import {ChevronUp} from "lucide-react";
import {models} from "@/schema/model-config";
import {useChatStore} from "@/store/chat-store";

export function ModelSelector() {
    const [open, setOpen] = useState(false)
    const chatStore = useChatStore()
    const [modelName, setModelName] = useState("")
    useEffect(() => {
        setModelName(chatStore.getCurrentSession().modelConfig.name)
    }, []);
    return <DropdownMenu modal={false} open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild >
            <Button variant={"ghost"}
                    className={"rounded-full overflow-x-hidden w-fit  flex flex-row items-center px-2 justify-end"}>
                <span className={"grow text-center text-sm sm:text-md"}>
                    {modelName}
                </span>
                <ChevronUp className={"transition stroke-foreground/60 " + (open ? "rotate-180" : "")}/>
            </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent side={"bottom"} className={"w-56 h-32"}>
            <div className={"w-full h-full overflow-y-auto"}>
                {models.map((it, index) => {
                    return <Button className={"w-full"} variant={"ghost"} key={index}
                                   onClick={() => {
                                       chatStore.updateCurrentSession(session => {
                                           session.modelConfig = it
                                           return session
                                       })
                                       setModelName(it.name)
                                       setOpen(false)
                                   }}
                    >
                        <span className={"w-full text-start "}>{it.name}</span>
                    </Button>
                })}
            </div>
        </DropdownMenuContent>
    </DropdownMenu>
}