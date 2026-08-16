# Agent Harness

> A modular harness for building reliable AI agents.

Agent Harness provides the infrastructure around a model: state, context, memory, planning, tools, perception, execution, and extension points. The goal is to make agent behavior easier to compose, inspect, and improve without coupling every experiment to one monolithic application.

## Why this repository exists

An agent is more than a model call. Useful systems need clear contracts for what the agent knows, how it decides, what it can do, and how each action is observed. This repository keeps those responsibilities separate while making them work as one runtime.

## Architecture

```text
agent-harness/
├── runtime/       # Lifecycle, state, events, and orchestration
├── context/       # Context assembly, budgeting, and retrieval
├── memory/        # Short- and long-term memory interfaces
├── planner/       # Task decomposition and policy selection
├── tools/         # Tool contracts, registry, and invocation
├── perception/    # Inputs from text, files, browser, and other modalities
├── execution/     # Action execution, retries, and recovery
├── plugins/       # Extension points and integrations
├── examples/      # End-to-end reference agents
└── design-notes/  # Architecture decisions and design explorations
```

## Design principles

- **Composable:** each subsystem has a small, explicit interface.
- **Observable:** important decisions and actions produce inspectable events.
- **Replaceable:** planners, memory backends, and tools can evolve independently.
- **Recoverable:** execution failures are expected, classified, and handled.
- **Evaluation-ready:** runs emit traces that can be consumed by `agent-evaluation`.

## Roadmap

- [ ] Define the minimal runtime and event model
- [ ] Specify context, memory, and tool interfaces
- [ ] Add one complete reference agent in `examples/`
- [ ] Emit a stable trace format for evaluation
- [ ] Add plugin discovery and lifecycle hooks

## Relationship to Agent Evaluation

Agent Harness builds and runs agents. [**Agent Evaluation**](https://github.com/tinaxiaxiao/agent-evaluation) consumes their tasks, outputs, and traces to measure quality, reliability, cost, and regressions.

## Status

Early design and scaffolding. Interfaces will change while the first end-to-end example is built.
