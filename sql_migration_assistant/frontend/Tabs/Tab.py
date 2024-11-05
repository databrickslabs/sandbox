from abc import ABC, abstractmethod

import gradio as gr


class Tab(ABC):
    header: gr.Markdown
    label: str
    tab: gr.Tab

    def __init__(self, header: str, label: str, **kwargs):
        with gr.Tab(label=label, *+kwargs) as tab:
            self.header = gr.Markdown(header)
            self.tab = tab
            self.build()

    @abstractmethod
    def build(self):
        """Build your Tab components here. Use self. to store components you need again"""
        pass
