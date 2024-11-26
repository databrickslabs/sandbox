import gradio as gr


class FeedbackTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Instructions") as self.tab:
            self.header = gr.Markdown(
                """
        ## Comments? Feature Suggestions? Bugs?
        
        Below is the link to the Legion Github repo for you to raise an issue. 
        
        On the right hand side of the Issue page, please assign it to **robertwhiffin**, and select the project **Legion**. 
        Raise the issue on the Github repo for Legion [here](https://github.com/databrickslabs/sandbox/issues/new).        
        """
            )
