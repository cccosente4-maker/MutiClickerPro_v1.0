# 🎯 MultiClickerPro

A professional Python auto-clicker with GUI built using Tkinter.

## Features
- Add multiple click positions
- Single & double click modes
- Save/load positions (JSON)
- Hotkeys: **F6 = Start**, **F7 = Stop**
- Visual overlays & sound effects

## Requirements
```bash
pip install -r requirements.txt
```

## Run
```bash
python multiclicker_pro.py
```

## Debugging in VS Code
Make sure you have `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Python File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```
