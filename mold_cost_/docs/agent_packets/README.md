# Agent 分发索引

本目录用于给并行执行的 agent 分发任务。

使用方式：

- 先发对应的 `*_BRIEF.md`
- 再把对应的 `*_PROMPT.md` 原文发给 agent
- 所有 agent 都以 [REFACTOR_AGENT_PARALLEL_PLAN.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/REFACTOR_AGENT_PARALLEL_PLAN.md) 为总约束

文件列表：

- [AGENT_0_PLAYBOOK.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_0_PLAYBOOK.md)
- [AGENT_1_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_1_BRIEF.md)
- [AGENT_1_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_1_PROMPT.md)
- [AGENT_2_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_2_BRIEF.md)
- [AGENT_2_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_2_PROMPT.md)
- [AGENT_3_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_3_BRIEF.md)
- [AGENT_3_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_3_PROMPT.md)
- [AGENT_4_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_4_BRIEF.md)
- [AGENT_4_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_4_PROMPT.md)
- [AGENT_5_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_5_BRIEF.md)
- [AGENT_5_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_5_PROMPT.md)
- [AGENT_6_BRIEF.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_6_BRIEF.md)
- [AGENT_6_PROMPT.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/agent_packets/AGENT_6_PROMPT.md)

推荐分发顺序：

1. Agent 4
2. Agent 3
3. Agent 1
4. Agent 2
5. Agent 5
6. Agent 6

说明：

- Agent 0 由当前主控负责，不需要额外分发。
- Agent 4 的目录当前已经存在未提交改动，优先发给同一个负责 pricing bridge 的执行者。
