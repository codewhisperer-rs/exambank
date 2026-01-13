import React, {useState} from "react";
import {useMediaQuery} from "react-responsive";
import {Dialog, DialogClose, DialogContent, DialogHeader, DialogTrigger} from "@/components/ui/dialog";
import {Drawer, DrawerContent} from "@/components/ui/drawer";
import {Button} from "@/components/ui/button";
import {LayoutList, Pencil, PlusIcon, X} from "lucide-react";
import {useChatStore} from "@/store/chat-store";
import {ChatSession, defaultChatSession, presetChatSessions} from "@/schema/chat-session";
import {DialogBody} from "next/dist/client/components/react-dev-overlay/ui/components/dialog";
import {useLanguageStore} from "@/store/language-store";

interface SessionSelectorProps {
    open: boolean,
    setOpen: (open: boolean) => void,
    trigger: React.ReactNode
}

export function SessionSelector() {
    const [open, setOpen] = useState(false)
    const mobile = useMediaQuery({maxWidth: 640})
    const trigger = <Button variant={"ghost"} className={"w-10 h-10 rounded-md p-2"} onClick={() => {
        setOpen(true)
    }}>
        <LayoutList/>
    </Button>
    const props = {
        trigger,
        setOpen,
        open,
    }
    return mobile ? <SessionSelectorMobile {...props}/> :
        <SessionSelectorPc {...props}/>
}

function SessionSelectorPc(props: SessionSelectorProps) {
    return <Dialog open={props.open} onOpenChange={(v) => props.setOpen(v)}>
        {props.trigger}
        <DialogContent className={"max-w-[600px] w-[600px] h-[600px]"}>
            <SessionSelectorContent {...props}/>
        </DialogContent>
    </Dialog>
}

function SessionSelectorMobile(props: SessionSelectorProps) {
    return <Drawer open={props.open} onOpenChange={(v) => props.setOpen(v)}>
        {props.trigger}
        <DrawerContent className={"w-full max-h-[70vh] h-[70vh]"}>
            <SessionSelectorContent {...props}/>
        </DrawerContent>
    </Drawer>
}

export function SessionSelectorContent(props: SessionSelectorProps) {
    const chatStore = useChatStore()
    const language = useLanguageStore().language
    return <div className={"w-full h-[85%] flex items-center justify-center"}>
        <div
            className={"h-[90%] w-[90%] overflow-y-auto"}>
            <div className={"w-full my-2 flex flex-row items-center justify-between"}>
                <h1 className={"select-none text-foreground/60 text-xl font-bold"}>Navigator</h1>
                <Button variant={"ghost"}>
                    Show all
                </Button>
            </div>
            {
                presetChatSessions.map((it, value) => {
                    return <Button variant={"ghost"} className={"w-full flex flex-row items-center justify-start gap-5"}
                    onClick={() => {
                        
                        chatStore.setChatStore(prev => {
                            return {
                                ...prev,
                                sessions: prev.sessions?.concat(it.session),
                                currentSessionIndex: prev.sessions?.length,
                            }
                        })
                        props.setOpen(false)
                    }}>
                <PlusIcon/>
                <span className={"text-lg w-full text-center font-semibold"}>
                    {it.name}
                </span>
            </Button>
                })
            }
            
            <div className={"w-full my-2 flex flex-row items-center justify-between"}>
                <h1 className={"select-none text-foreground/60 text-xl font-bold mb-4"}>Recent</h1>

            </div>
            {chatStore.sessions.map((session, index) => {
                return <SessionItem closeSelector={() => {
                    props.setOpen(false)
                }} session={session} index={index}></SessionItem>
            })}
        </div>
    </div>
}

function SessionItem(props: { session: ChatSession, index: number, closeSelector: () => void }) {
    const chatStore = useChatStore()
    const language = useLanguageStore().language
    const [sessionNewName, setSessionNewName] = useState(props.session.name)
    return <div className={"h-12 w-full flex flex-row items-center justify-start gap-5"}>
        <Button
            variant={"ghost"}
            onClick={() => {
                chatStore.setChatStore(prev => {
                    return {
                        ...prev,
                        currentSessionIndex: props.index,
                    }
                })
                props.closeSelector()
            }}
            className={"grow"}>
                        <span className={"text-lg grow text-center"}>
                            {props.session.name}
                        </span>

        </Button>
        <div className={"flex flex-row w-fit"}>
            <Dialog>
                <DialogTrigger>
                    <Button variant={"ghost"} className={""}>
                        <Pencil/>
                    </Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        {language["chat-session-selector.session.rename.dialog.title"]}
                    </DialogHeader>
                    <DialogBody className={"flex flex-col gap-5 items-center w-full h-full"}>
                        <input value={sessionNewName}
                               className={"w-[80%] border-[1px] border-primary/40 px-4 py-2 rounded-md"}
                               onChange={event => {
                                   setSessionNewName(event.target.value)
                               }}/>
                        <div className={"flex flex-row w-[80%] gap-2 items-center justify-around"}>
                            <DialogClose className={"w-[40%]"}>
                                <Button className={"w-full"} variant={"secondary"}>{language["cancel"]}</Button>
                            </DialogClose>
                            <DialogClose className={"w-[40%]"}>
                                <Button className={"w-full"} onClick={() => {
                                    chatStore.updateCurrentSession(prev => {
                                        return {
                                            ...prev,
                                            name: sessionNewName,
                                        }
                                    })
                                }}>{language["confirm"]}</Button>
                            </DialogClose>
                        </div>
                    </DialogBody>
                </DialogContent>
            </Dialog>
            <Dialog>
                <DialogTrigger>
                    <Button variant={"ghost"}>
                        <X/>
                    </Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>

                        {language["chat-session-selector.session.delete.dialog.title"]}
                    </DialogHeader>
                    <DialogBody className={"flex flex-col gap-5 items-center w-full h-full"}>
                        <div className={"w-[80%] text-center"}>
                            {language["chat-session-selector.session.delete.dialog.content"]}
                        </div>
                        <div className={"flex flex-row w-[80%] gap-2 items-center justify-around"}>
                            <DialogClose className={"w-[40%]"}>
                                <Button className={"w-full"} variant={"secondary"}>{language["cancel"]}</Button>
                            </DialogClose>
                            <DialogClose className={"w-[40%]"}>
                                <Button className={"w-full"} onClick={() => {
                                    chatStore.removeSession(props.index)
                                }}>{language["confirm"]}</Button>
                            </DialogClose>
                        </div>
                    </DialogBody>
                </DialogContent>
            </Dialog>
        </div>
    </div>
}