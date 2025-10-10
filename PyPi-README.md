# Vehicle Specification Editor

A graphical user interface for editing, compiling, and verifying Vehicle language specifications.

## Features

- **Code Editor**: Syntax highlighting for Vehicle (.vcl) files
- **File Operations**: New, Open, Save for specification files
- **Compilation**: Compile specifications with view of query graph
- **Verification**: Run verification using Marabou
- **Resource Management**: Load networks, datasets, and parameters using filesystem
- **Counterexamples**: Visual representation of counterexamples and witnesses

## Requirements

- Python 3.10+
- Marabou verifier (for verification)

## Usage

```bash
vehicle_gui
```

1. Open a Vehicle specification file (.vcl)
2. Load required resources (auto-detected)
3. Set verifier path if needed
4. Compile or verify specification
5. View results in console and results tabs

# Change Log
- Auto-discover Marabou installations
- View unique quantified variables for each property
- Add side-by-side view of query tree and query text

## License

MIT License

