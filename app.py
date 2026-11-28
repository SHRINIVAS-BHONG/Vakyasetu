import sys
import os
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# If this file was imported as 'app' (e.g. `import app`), sys.modules['app'] is this script.
# Temporarily remove it so Python resolves 'app' to the backend/app package.
_this_module = sys.modules.get("app")
if _this_module is not None and not hasattr(_this_module, "__path__"):
    del sys.modules["app"]

try:
    import spaces
except ImportError:
    class _MockSpaces:
        def GPU(self, fn=None, **kwargs):
            if fn is None:
                return lambda f: f
            return fn
    spaces = _MockSpaces()

if spaces is not None:
    @spaces.GPU
    def _zero_gpu_marker():
        """Marker function required by Hugging Face ZeroGPU environment during startup inspection."""
        pass

import gradio as gr
from app.main import app as fastapi_app

# Define a lightweight Gradio interface mounted at /gradio to satisfy the Gradio Space harness
with gr.Blocks(title="वाक्यसेतु · VākyaSetu") as demo:
    gr.Markdown("# 📜 वाक्यसेतु · VākyaSetu\n\nThe full interactive React application is live at the root path: [/](/).")

# Mount Gradio at /gradio so root '/' and '/assets' serve the project's original React + Vite UI
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

# Restore module reference if imported
if _this_module is not None:
    _this_module.demo = demo
    _this_module.app = app
    sys.modules["app"] = _this_module

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
