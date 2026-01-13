
import {Button} from "@/components/ui/button";
import {FileIcon, UploadIcon} from "lucide-react";
import {useMediaQuery} from "react-responsive";
import {Dialog, DialogContent, DialogHeader, DialogTitle} from "@/components/ui/dialog";
import {useState} from "react";
import {useLanguageStore} from "@/store/language-store";
import {Drawer, DrawerContent, DrawerHeader, DrawerTitle} from "@/components/ui/drawer";

export function AttachmentUploader(){
    const [open, setOpen] = useState(false)
    const mobile = useMediaQuery({maxWidth: 640})
    return mobile ? <UploaderMobile open={open} setOpen={setOpen}/> : <UploaderPc open={open} setOpen={setOpen}/>
}

interface UploaderProps {
    open: boolean,
    setOpen: (value: boolean) => void,
}

function UploaderMobile(props: UploaderProps) {
    const languageStore = useLanguageStore()
    return <Drawer open={props.open} onOpenChange={(v) => props.setOpen(v)}>
        <Button variant={"outline"} className={"rounded-full h-7 w-7 sm:h-10 sm:w-10 hover:cursor-pointer "}
                onClick={() => props.setOpen(true)}>
            <UploadIcon/>
        </Button>
        <DrawerContent className={"px-4 h-fit"}>
            <DrawerHeader className={"p-0 py-2"}>
                <DrawerTitle>{languageStore.language["input-box.attachment.title"]}</DrawerTitle>
            </DrawerHeader>
            <Uploader/>
        </DrawerContent>
    </Drawer>
}

function UploaderPc(props: UploaderProps) {
    const languageStore = useLanguageStore()
    return <Dialog open={props.open} onOpenChange={(v) => props.setOpen(v)}>
        <Button size={"icon"} variant={"outline"} className={"rounded-full h-10 w-10 hover:cursor-pointer "}
                onClick={() => props.setOpen(true)}>
            <UploadIcon/>
        </Button>
        <DialogContent className={"w-[512px] h-fit flex flex-col items-center px-4  select-none"}>
            <DialogHeader>
                <DialogTitle>{languageStore.language["input-box.attachment.title"]}</DialogTitle>
            </DialogHeader>
            <Uploader/>
        </DialogContent>
    </Dialog>
}

function Uploader() {
    const languageStore = useLanguageStore()
    return <>
        <div className={"h-[240px] w-full flex items-center justify-center rounded-md flex-col gap-3.5"}>
            <FileIcon className={"w-8 h-8 stroke-foreground/50"}/>
            <span
                className={"text-lg font-semibold"}>{languageStore.language['input-box.attachment.upload.label']}</span>
            <span
                className={"text-md font-medium text-foreground/30"}>{languageStore.language['input-box.attachment.upload.message']}</span>
            <Button variant={"secondary"}
                    className={"font-semibold text-sm text-foreground/80 hover:cursor-pointer"}>{languageStore.language["input-box.attachment.upload.button"]}</Button>
        </div>
        <div className={"w-full grow flex flex-col items-center justify-start h-[240px]"}>
                <span
                    className={"w-full text-start font-semibold"}>{languageStore.language["input-box.attachment.upload.recent"]}</span>
        </div>
    </>
}