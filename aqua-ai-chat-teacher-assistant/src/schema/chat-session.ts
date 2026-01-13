import {z} from "zod";
import {ChatMessageContentSchema, defaultGreetingMessage} from "@/schema/chat-message";
import {defaultModelConfig, ModelConfigSchema} from "@/schema/model-config";

export const ChatSessionSchema = z.object({
    messages: z.array(ChatMessageContentSchema),
    modelConfig: ModelConfigSchema,
    name: z.string(),
    streaming: z.boolean().nullable().optional(),
})
export type ChatSession = z.infer<typeof ChatSessionSchema>
export const defaultChatSession: ChatSession = {
    messages: [defaultGreetingMessage],
    modelConfig: defaultModelConfig,
    name: "New Conversation",
    streaming: false,
}
export const presetChatSessions = [
    {
        name: "新的对话",
        session: defaultChatSession,
    },
    {
        name: "数据结构与算法",
        session: {
            messages: [
                {
                    role: "assistant",
                    contents: [
                        "👋 欢迎进入《数据结构与算法》学习之旅！我是你的 AI 助教，期待陪伴你深入探索计算机科学的基础。\n" +
                        "我们将一起剖析数据的组织方式、探讨算法设计的思想与技巧，并通过实例掌握复杂问题的解决方案。\n" +
                        "\n" +
                        "你可以尝试点击这些问题，快速开启你的学习旅程："
                    ],
                    metaType: "greeting",
                    thinking: false,
                    suggestion: {
                        suggestions: [
                            {
                                message: "如何分析算法的时间复杂度和空间复杂度？",
                                title: "算法复杂度分析",
                                description: "理解大O表示法及算法效率分析方法"
                            },
                            {
                                message: "数组、链表、栈与队列各有什么特点和应用场景？",
                                title: "基础数据结构",
                                description: "掌握常见线性数据结构的特性与实现"
                            },
                            {
                                message: "树、图等非线性结构如何表示和遍历？",
                                title: "高级数据结构",
                                description: "学习树与图的实现及其算法"
                            },
                            {
                                message: "动态规划与贪心算法有什么区别和联系？",
                                title: "算法设计范式",
                                description: "掌握解决复杂问题的算法设计方法"
                            },
                            {
                                message: "红黑树的平衡调整原理是什么？",
                                title: "平衡树结构",
                                description: "了解自平衡树的工作原理"
                            },
                            {
                                message: "哈希表的冲突解决策略有哪些优缺点？",
                                title: "哈希表原理",
                                description: "理解哈希函数与冲突处理机制"
                            }
                        ]
                    }
                }
            ],
            modelConfig: defaultModelConfig,
            name: "数据结构与算法学习助手",
            streaming: false,
        },
    },
    {
        name: "操作系统原理",
        session: {
            messages: [
                {
                    role: "assistant",
                    contents: [
                        "👋 欢迎进入《操作系统》学习之旅！我是你的 AI 助教，期待陪伴你深入探索计算机系统的核心。\n" +
                        "我们将一起解析进程管理的原理、探讨内存分配的策略，并理解文件系统和I/O设备的管理机制。\n" +
                        "\n" +
                        "你可以尝试点击这些问题，快速开启你的学习旅程："
                    ],
                    metaType: "greeting",
                    thinking: false,
                    suggestion: {
                        suggestions: [
                            {
                                message: "进程与线程的区别及其通信方式有哪些？",
                                title: "进程与线程",
                                description: "理解并发编程的基本单位"
                            },
                            {
                                message: "如何通过页面置换算法优化虚拟内存管理？",
                                title: "内存管理",
                                description: "了解虚拟内存工作原理及优化方法"
                            },
                            {
                                message: "死锁的必要条件及预防策略是什么？",
                                title: "死锁问题",
                                description: "掌握并发系统中死锁的处理方法"
                            },
                            {
                                message: "CPU调度算法如何影响系统性能？",
                                title: "处理器调度",
                                description: "理解不同调度算法的优缺点"
                            },
                            {
                                message: "文件系统的索引结构如何影响读写效率？",
                                title: "文件系统",
                                description: "探索数据持久化存储的实现原理"
                            },
                            {
                                message: "如何设计高效的I/O系统以减少等待时间？",
                                title: "I/O管理",
                                description: "学习设备管理与驱动程序原理"
                            }
                        ]
                    }
                }
            ],
            modelConfig: defaultModelConfig,
            name: "操作系统学习助手",
            streaming: false,
        },
    },
    {
        name: "计算机组成原理",
        session: {
            messages: [
                {
                    role: "assistant",
                    contents: [
                        "👋 欢迎进入《计算机组成原理》学习之旅！我是你的 AI 助教，期待陪伴你探索计算机硬件系统的奥秘。\n" +
                        "我们将一起分析处理器的工作原理、了解指令系统的设计思想，并探讨存储层次与总线结构的实现机制。\n" +
                        "\n" +
                        "你可以尝试点击这些问题，快速开启你的学习旅程："
                    ],
                    metaType: "greeting",
                    thinking: false,
                    suggestion: {
                        suggestions: [
                            {
                                message: "冯·诺依曼体系结构的核心特点是什么？",
                                title: "计算机体系结构",
                                description: "理解现代计算机的基本架构"
                            },
                            {
                                message: "CPU的指令执行周期是如何工作的？",
                                title: "指令执行过程",
                                description: "了解指令获取、解码与执行的过程"
                            },
                            {
                                message: "流水线技术如何提高处理器的吞吐率？",
                                title: "流水线原理",
                                description: "探索提高CPU性能的关键技术"
                            },
                            {
                                message: "多级缓存结构如何解决存储器访问瓶颈？",
                                title: "存储层次结构",
                                description: "理解缓存设计与内存管理机制"
                            },
                            {
                                message: "RISC和CISC指令集架构各有什么优缺点？",
                                title: "指令集设计",
                                description: "比较不同指令系统的设计思想"
                            },
                            {
                                message: "总线仲裁机制如何解决访问冲突问题？",
                                title: "总线与接口",
                                description: "学习系统组件间的通信原理"
                            }
                        ]
                    }
                }
            ],
            modelConfig: defaultModelConfig,
            name: "计算机组成原理学习助手",
            streaming: false,
        },
    },
    {
        name: "计算机网络",
        session: {
            messages: [
                {
                    role: "assistant",
                    contents: [
                        "👋 欢迎进入《计算机网络》学习之旅！我是你的 AI 助教，期待陪伴你深入了解互联世界的技术基础。\n" +
                        "我们将一起探索网络协议的分层模型、分析数据传输的可靠性机制，并理解网络安全与应用层服务的实现原理。\n" +
                        "\n" +
                        "你可以尝试点击这些问题，快速开启你的学习旅程："
                    ],
                    metaType: "greeting",
                    thinking: false,
                    suggestion: {
                        suggestions: [
                            {
                                message: "OSI七层模型与TCP/IP四层模型有什么区别和联系？",
                                title: "网络分层模型",
                                description: "理解网络协议的基本框架"
                            },
                            {
                                message: "TCP的三次握手和四次挥手过程为何这样设计？",
                                title: "TCP连接管理",
                                description: "掌握可靠连接的建立与终止机制"
                            },
                            {
                                message: "IP地址分类与子网划分如何计算与应用？",
                                title: "网络寻址",
                                description: "学习IPv4地址规划与子网掩码"
                            },
                            {
                                message: "路由选择算法如何影响数据包的传输路径？",
                                title: "路由协议",
                                description: "了解网络中数据转发决策机制"
                            },
                            {
                                message: "HTTPS的加密和身份验证机制是如何保障安全的？",
                                title: "网络安全",
                                description: "探索密钥交换与证书验证过程"
                            },
                            {
                                message: "CDN和负载均衡如何提升网络应用性能？",
                                title: "网络优化技术",
                                description: "理解提高网络服务效率的关键技术"
                            }
                        ]
                    }
                }
            ],
            modelConfig: defaultModelConfig,
            name: "计算机网络学习助手",
            streaming: false,
        },
    }
  
]