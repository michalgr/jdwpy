# Agent Guidelines & Quality Control

Before completing a task, submitting work, or proposing git commits, you MUST run the following validation steps to ensure code quality and correctness:

## 1. Code Formatting
Ensure all Python files are correctly formatted using Ruff.
- Command: `uv run ruff format` (can be run directly)

## 2. Testing
Ensure the complete test suite (both unit and integration tests) passes successfully.
- Command (MUST be run via nix-shell to guarantee Java dependencies `java` and `javac` are present):
  ```bash
  nix-shell --run "uv run pytest"
  ```

## 3. Type Checking
Ensure that type annotations are correct and run the typechecker (Pyre).
- Command:
  ```bash
  uv run pyrefly
  ```
