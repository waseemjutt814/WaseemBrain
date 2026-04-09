# Agent v2 - OCaml Agent Framework

A high-level, powerful agent framework written in **OCaml** for the WaseemBrain project.

## Features

- 🚀 **Lightweight & Fast**: Built with OCaml's performance characteristics
- 🔄 **Async/Await**: Full Lwt (Light Weight Thread) support for concurrent operations
- 🧠 **State Management**: Sophisticated agent state tracking and message history
- 🛠️ **Action System**: Extensible action execution (Execute, ReadFile, WriteFile, HttpRequest, Search, Think)
- 📦 **Context Management**: Key-value context store for session persistence
- ⏱️ **Timeout Handling**: Configurable timeouts for all operations
- 🔗 **Action Chaining**: Compose multiple actions into sequential workflows

## Project Structure

```
agent-v2/
├── lib/
│   ├── agent.ml          # Core agent implementation
│   ├── agent.mli         # Public interface
│   └── dune              # Library build config
├── bin/
│   ├── main.ml           # Demo executable
│   └── dune              # Executable build config
├── dune-project          # Dune project configuration
└── README.md             # This file
```

## Installation

```bash
# Install dependencies
opam install dune lwt lwt_ppx

# Build the project
dune build

# Run the demo
dune exec agent-v2
```

## Quick Start

```ocaml
open Agent

let config = {
  id = "my_agent";
  name = "My Agent";
  version = "1.0.0";
  max_actions = 100;
  timeout_seconds = 60.0;
  enable_thinking = true;
}

let agent = create_agent config
let message = create_message User "Hello, Agent!"

(* Process the message *)
let result = Lwt_main.run (process_message agent message)
```

## Agent Configuration

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique agent identifier |
| `name` | string | Human-readable name |
| `version` | string | Version string |
| `max_actions` | int | Maximum actions per session |
| `timeout_seconds` | float | Default timeout for operations |
| `enable_thinking` | bool | Enable reasoning/thinking steps |

## Actions

The framework supports these action types:

- `Execute (cmd, args)` - Execute system commands
- `ReadFile path` - Read file contents
- `WriteFile (path, content)` - Write content to file
- `HttpRequest (method, url, headers)` - Make HTTP requests
- `Search (pattern, scope)` - Search for patterns
- `Think reasoning` - Internal reasoning step

## License

MIT License - See LICENSE file for details.

## Author

Waseem - [GitHub](https://github.com/waseemjutt814)
