"""People 评审子模块 —— OSINT V6 政治人物报告三专家 LLM 评审流水线。

本模块作为 news-monitor 项目的独立附加模块，只读访问 src/news_monitor 下的
proxy / cloubic 基础能力，不修改主项目代码。

评审流程：
    1. 加载目标 .docx 报告并提取正文
    2. 加载 V6 框架要点
    3. 分别以三位专家角色调用三个不同 LLM 通道
    4. 汇总输出 markdown 评审报告
"""
