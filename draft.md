# What agentic coding actually is (draft)

Everyone is shipping "agents" now. Most of what gets called an agent is a
workflow with a nicer name. Here is the part that survives contact with a real
codebase.

Anthropic draws the line explicitly: agents are systems where LLMs dynamically
direct their own processes and tool usage, maintaining control over how they
accomplish tasks. Workflows, by contrast, are orchestrated through predefined
code paths.

Claude Code is Anthropic's agentic coding tool that lives in your terminal and
understands your codebase.

The interface the agent gets matters more than people expect. The SWE-agent
paper introduced the Agent-Computer Interface (ACI) and showed that
LLM-centric commands and environment feedback make agents substantially more
useful for software engineering.

Multi-agent debate is a real evaluation technique, not just a demo. ChatEval
built a multi-agent referee team to autonomously discuss and evaluate the
quality of generated text.

Simon Willison's working definition is the one that stuck for most people: an
LLM agent runs tools in a loop to achieve a goal.

MCP is how you stop writing one adapter per tool. The Model Context Protocol is
an open protocol that standardizes how applications provide context to LLMs.

Cursor lets you steer the model with persistent project rules that are checked
into the repo.

Anthropic's own build-with-claude guide documents the agent loop pattern for
tool use.

The gap between a demo and a product is verification. If the agent cannot check
its own work against something outside itself, you are the verification layer.
