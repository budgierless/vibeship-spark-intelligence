# Cursor / VS Code tasks (copy-paste)

Create `.vscode/tasks.json` in your project:

```json
{
  "version": "2.0.0",
  "inputs": [
    {"id": "tasteText", "type": "promptString", "description": "Paste URL/text you like"},
    {"id": "rememberText", "type": "promptString", "description": "What should Spark remember?"}
  ],
  "tasks": [
    {
      "label": "Spark: Remember",
      "type": "shell",
      "command": "python3 ${workspaceFolder}/scripts/emit_event.py --source cursor --kind command --session ${workspaceFolderBasename} --intent remember --text \"${input:rememberText}\" | python3 ${workspaceFolder}/adapters/stdin_ingest.py --sparkd ${SPARKD_URL:-http://127.0.0.1:${SPARKD_PORT:-8787}}",
      "problemMatcher": []
    },
    {
      "label": "Spark: Like (post/UI/art)",
      "type": "shell",
      "command": "python3 ${workspaceFolder}/scripts/emit_event.py --source cursor --kind message --session ${workspaceFolderBasename} --role user --text \"I like this: ${input:tasteText}\" | python3 ${workspaceFolder}/adapters/stdin_ingest.py --sparkd ${SPARKD_URL:-http://127.0.0.1:${SPARKD_PORT:-8787}}",
      "problemMatcher": []
    }
  ]
}
```

Then run the tasks from Cursor/VSCode command palette.

If you override ports, replace `8787` or set `SPARKD_URL` and update the task command.
