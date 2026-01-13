import Markdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import "katex/dist/katex.min.css";
import React from "react";

export function MarkdownViewer(props: { content: string }) {
    // 创建一个ref来跟踪行号
    const rowIndexRef = React.useRef(0);
    
    // 在每次渲染前重置行索引
    React.useEffect(() => {
        rowIndexRef.current = 0;
    }, [props.content]);
    
    return (
        <div className="markdown-body">
            <Markdown 
                remarkPlugins={[remarkMath, remarkGfm]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    // 为表格元素直接添加内联样式
                    table: ({...props}) => (
                        <table 
                            style={{
                                width: "100%",
                                borderCollapse: "collapse",
                                margin: "1rem 0"
                            }} 
                            {...props} 
                        />
                    ),
                    th: ({...props}) => (
                        <th 
                            style={{
                                border: "1px solid #ddd",
                                padding: "8px",
                                textAlign: "left",
                                backgroundColor: "#f2f2f2",
                                fontWeight: "bold"
                            }} 
                            {...props} 
                        />
                    ),
                    td: ({...props}) => (
                        <td 
                            style={{
                                border: "1px solid #ddd",
                                padding: "8px",
                                textAlign: "left"
                            }} 
                            {...props} 
                        />
                    ),
                    tr: ({children, ...props}) => {
                        // 为奇偶行添加不同样式
                        const isEven = rowIndexRef.current++ % 2 === 1;
                        return (
                            <tr 
                                style={{
                                    borderTop: "1px solid #ddd",
                                    backgroundColor: isEven ? "#f9f9f9" : undefined
                                }} 
                                {...props}
                            >
                                {children}
                            </tr>
                        );
                    }
                }}
            >
                {props.content}
            </Markdown>
        </div>
    );
}