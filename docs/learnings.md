# Learnings

Personal notes from building micro-agent.

## Session 1 — Bare chat loop
- agent = model + harness (i.e. code around the agent)
- Understood the core of the "while" loop that drives agents: user input --> model 1st forward pass --> feedbac to model along with user input --> model 2nd forward pass --> and so on.
- Understood the value of the plumbing - loading the environment, the config, the openrouter "comms", basic error handling
- Understood the value of the message building queue and how the agent creates 'memory' for the model
- Models are powerful! Even a handful of instructions and a few hundred lines of code are enough for "intelligence"
- What is your differentiation - both in personal and professional workflows - is critical yet hard to determine. Esp for software based workflows. Because agents can (or soon can) interact with nearly all software
-

## Session 2 — Web search tool loop
- Tools extend model capabilities in two ways: Get new information/data that is outside of their training data + execute actions in other software systems
- Understood that tools need two things: tool schema (for the agent) and the actual tool use code
- Tool use is 'suggested' to the model, not mandated. The model decides when it wants to use a tool (insane). Equivalent of telling an intern 'you have excel, I suggest you use excel but upto you bro"
- Building tools will be critical, probably hard, yet undifferentiated

## Session 3 — Slash commands and docs
- This entire session was just overkill
- Agents.md is useful as various coding agents will work on this repo but beyond that it's all garbage

## Session 4 - Sub agents
- Verifier agents for QC
- XX
- XX
