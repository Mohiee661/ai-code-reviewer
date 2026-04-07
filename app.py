import gradio as gr

def review_code(code):
    # simple placeholder logic
    return f"Review:\n\nYour code looks fine 👍\n\nInput was:\n{code}"

demo = gr.Interface(
    fn=review_code,
    inputs=gr.Textbox(lines=10, placeholder="Paste your code here..."),
    outputs="text",
    title="AI Code Reviewer"
)

demo.launch()