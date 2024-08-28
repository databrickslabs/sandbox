Using Legion
####################


Usage of Legion is simple; paste code into the editor, and press the "Translate"
button. The code will be automatically translated into the target language. and presented
in the output window.

.. image:: ../images/translation_screen.png
    :width: 844px
    :height: 436px
    :alt: Legion Translation Screen
    :align: center

Once you have translated your code, you can copy and paste it into Databricks to run it.
Coming soon this will be automated.

Migration SMEs and advanced users will need to tune the system prompt to get the best
performance for the translation. This is done in the Advanced tab above the Translation
screen. This is the example prompt included for a T-SQL to Spark SQL translation.

.. image:: ../images/translation_prompt.png
    :width: 840px
    :height: 566px
    :alt: Legion Translation Prompt
    :align: center

The next step is to extract the intent of the code. This is done by clicking the "Extract
Intent" button. This will present the intent back to the user in the below chat screen.
The chat interface allows the user to refine the intent statement in conversation with
the AI Agent. As with code translation, the Advanced tab can be used to tune the system
prompt, for example to add in business specific knowledge such as acronyms or domain jargon.

.. image:: ../images/intent_generation.png
    :width: 830px
    :height: 300px
    :alt: Legion Intent Generation
    :align: center

Finally, the user will click the "Save intent and code" button once the intent is refined.
This will store the intent and code in the database for future reference and discoverability.

.. image:: ../images/similar_code.png
    :width: 820px
    :height: 412px
    :alt: Legion Similar Code
    :align: center
