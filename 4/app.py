import gradio as gr
from sidekick import Sidekick

async def setup():
    try:
        sidekick = Sidekick()
        await sidekick.setup()
        print("Setup completed successfully")
        return sidekick
    except Exception as e:
        print(f"Setup FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def process_message(sidekick, message, success_criteria, history):
    results =await sidekick.run_superstep(message, success_criteria, history)
    return results, sidekick


async def reset():
    new_sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, new_sidekick


def free_resources(sidekick: Sidekick):
    print("cleaning UP")
    try:
        if sidekick:
            sidekick.cleanup()
    except Exception as e:
        print(f"Error freeing resources: {e}")

with gr.Blocks(title='Sidekick') as ui:
    gr.Markdown("# Sidekick")
    sidekick = gr.State(delete_callback=free_resources)

    with gr.Row():
        chatbot = gr.Chatbot(label='Sidekick', height=300)
    with gr.Group():
        with gr.Row():
            message = gr.Textbox(show_label=False, placeholder="Enter your request here...")
            with gr.Row():
                success_criteria = gr.Textbox(
                    show_label=False, placeholder="Enter the success criteria for this request..."
                )
    with gr.Row():
        reset_button = gr.Button('Reset', variant='stop')
        go_button = gr.Button('Go', variant='primary')
    
    ui.load(setup, [], [sidekick])
    message.submit(
        process_message,[sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    success_criteria.submit(
        process_message, [sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    go_button.click(
        process_message, [sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    reset_button.click(reset, [], [message, success_criteria, chatbot, sidekick])

ui.launch(inbrowser=True)
