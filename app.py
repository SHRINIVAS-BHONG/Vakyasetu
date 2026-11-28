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

import gradio as gr
try:
    import spaces
except ImportError:
    class _MockSpaces:
        def GPU(self, fn=None, **kwargs):
            if fn is None:
                return lambda f: f
            return fn
    spaces = _MockSpaces()

from app.services.orchestrator import get_orchestrator_service

# Pre-warm orchestrator
orchestrator = get_orchestrator_service()

@spaces.GPU
def analyze_sanskrit(sentence: str):
    if not sentence or not sentence.strip():
        return (
            "⚠️ Please enter a Sanskrit sentence to analyze.",
            "None",
            [],
            "No input provided."
        )
    
    try:
        res = orchestrator.analyze(sentence.strip())
        
        # 1. Translation
        translation_text = f"### 📖 English Translation\n\n> **{res.translation}**\n\n*Processing Time: {res.processing_time_ms:.1f} ms*"
        
        # 2. Sandhi Splits & Rules
        splits_str = "  ✦  ".join(res.sandhi_splits)
        rules_text = "### ✂️ Sandhi Segmentation\n\n"
        rules_text += f"**Constituent Words (पदानि):**\n`{splits_str}`\n\n"
        if res.sandhi_rules:
            rules_text += "**Applied Paninian Rules (सन्धिनियम):**\n"
            for r in res.sandhi_rules:
                rules_text += f"- **{r.rule_name}** (`{r.panini_sutra}`): `{r.input_segment}` → `{r.output_segment}` ({r.description})\n"
        else:
            rules_text += "*No Sandhi fusion detected or single-word constituents.*"
            
        # 3. Morphology Table
        morph_rows = []
        for m in res.morphology:
            pg = m.primary_gloss
            root = pg.root if pg else "—"
            pos = pg.pos if pg else "—"
            case = pg.case if pg and pg.case else "—"
            number = pg.number if pg and pg.number else "—"
            gender = pg.gender if pg and pg.gender else "—"
            karaka = m.karaka_role if m.karaka_role else "—"
            explanation = pg.english_explanation if pg and pg.english_explanation else "—"
            morph_rows.append([m.word, root, pos, case, number, gender, karaka, explanation])
            
        # 4. Grammar Alerts
        if res.grammar_warnings:
            grammar_text = "### ⚠️ Grammar Concordance Warnings\n\n"
            for gw in res.grammar_warnings:
                grammar_text += f"- **{gw}**\n"
        else:
            grammar_text = "### ✅ Paninian Grammar Concordance Validated\n\n- **Subject-Verb Agreement (पुरुष-वचन-अन्वयः):** Verified\n- **Case & Upapada Governance (विभक्ति-अन्वयः):** Verified\n- **Sentence Completeness (वाक्य-पूर्तता):** Complete"

        return translation_text, rules_text, morph_rows, grammar_text
    except Exception as e:
        return (
            f"❌ Error during analysis: {str(e)}",
            "Error",
            [],
            f"Pipeline error: {str(e)}"
        )

# Define Gradio Theme & Blocks
custom_theme = gr.themes.Soft(
    primary_hue="amber",
    secondary_hue="stone",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Noto Serif Devanagari"), gr.themes.GoogleFont("Source Serif 4"), "ui-serif", "serif"]
)

custom_css = """
.gradio-container {
    max-width: 1050px !important;
    margin: auto !important;
    padding-top: 1.5rem !important;
}
.header-box {
    text-align: center;
    margin-bottom: 1.5rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, #fef3c7 0%, #ffedd5 100%);
    border-radius: 12px;
    border: 1px solid #fde68a;
}
.header-box h1 {
    color: #92400e;
    margin: 0;
    font-size: 2.2rem;
}
.header-box p {
    color: #78350f;
    margin: 0.5rem 0 0 0;
    font-size: 1.05rem;
}
"""

with gr.Blocks(theme=custom_theme, css=custom_css, title="वाक्यसेतु · VākyaSetu") as demo:
    gr.HTML(
        """
        <div class="header-box">
            <h1>📜 वाक्यसेतु · VākyaSetu</h1>
            <p><strong>Computational Sanskrit Sandhi, Morphology & Translation Engine (CBSE/NCERT Classes 6–10)</strong></p>
            <p style="font-size: 0.95rem; opacity: 0.85;">Paste any Sanskrit sentence to receive an accurate English translation, Sandhi separation, and Paninian grammatical breakdown.</p>
        </div>
        """
    )
    
    with gr.Row():
        with gr.Column(scale=4):
            input_text = gr.Textbox(
                label="संस्कृत-वाक्यम् (Enter Sanskrit Sentence)",
                placeholder="उदा. बालकः पुस्तकं पठति।",
                value="बालकः पुस्तकं पठति।",
                lines=2,
            )
        with gr.Column(scale=1):
            analyze_btn = gr.Button("🔍 Analyze Sentence (विश्लेषणम्)", variant="primary", size="lg")
            clear_btn = gr.ClearButton(value="Clear")

    gr.Markdown("**Quick NCERT Examples:**")
    with gr.Row():
        ex1 = gr.Button("बालकः पुस्तकं पठति।", size="sm")
        ex2 = gr.Button("वयं विद्यालये पठामः।", size="sm")
        ex3 = gr.Button("सः सदा सत्यं वदति।", size="sm")
        ex4 = gr.Button("रामः जनकेन सह वनम् अगच्छत्।", size="sm")

    with gr.Tabs():
        with gr.TabItem("📖 Translation (अनुवादः)"):
            out_translation = gr.Markdown()
        with gr.TabItem("✂️ Sandhi Segmentation (सन्धि-विच्छेदः)"):
            out_sandhi = gr.Markdown()
        with gr.TabItem("🏷️ Morphological Breakdown (पद-विश्लेषणम्)"):
            out_morph = gr.Dataframe(
                headers=["Word (पदम्)", "Root (धातु/प्रातिपदिक)", "POS", "Vibhakti (विभक्तिः)", "Vacana (वचनम्)", "Linga (लिङ्गम्)", "Kāraka Role", "Explanation"],
                datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                interactive=False,
            )
        with gr.TabItem("🛡️ Grammar Checker (दोष-परीक्षकः)"):
            out_grammar = gr.Markdown()

    gr.Markdown(
        """
        ---
        *Developed for CBSE/NCERT Sanskrit students & teachers.* | **API Documentation:** Visit [`/docs`](/docs) | **System Health:** [`/health`](/health)
        """
    )

    outputs = [out_translation, out_sandhi, out_morph, out_grammar]

    analyze_btn.click(fn=analyze_sanskrit, inputs=[input_text], outputs=outputs)
    ex1.click(fn=lambda: "बालकः पुस्तकं पठति।", outputs=[input_text]).then(fn=analyze_sanskrit, inputs=[input_text], outputs=outputs)
    ex2.click(fn=lambda: "वयं विद्यालये पठामः।", outputs=[input_text]).then(fn=analyze_sanskrit, inputs=[input_text], outputs=outputs)
    ex3.click(fn=lambda: "सः सदा सत्यं वदति।", outputs=[input_text]).then(fn=analyze_sanskrit, inputs=[input_text], outputs=outputs)
    ex4.click(fn=lambda: "रामः जनकेन सह वनम् अगच्छत्।", outputs=[input_text]).then(fn=analyze_sanskrit, inputs=[input_text], outputs=outputs)
    clear_btn.add([input_text, out_translation, out_sandhi, out_morph, out_grammar])

# Expose demo as app for ASGI runners if needed
app = demo

# If this file was imported as 'app', restore this module into sys.modules so callers can access demo
if _this_module is not None:
    _this_module.demo = demo
    _this_module.app = app
    sys.modules["app"] = _this_module

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, theme=custom_theme, css=custom_css)
