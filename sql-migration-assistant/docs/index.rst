Welcome to Legion's documentation!

Documentation
=============

.. toctree::
   :glob:
   :titlesonly:
   :maxdepth: 2
   :caption: Contents:

   usage/installation
   usage/usage


Legion is a Databricks field project to accelerate migrations on to Databricks leveraging the platform’s generative AI
capabilities. It uses an LLM for code conversion and intent summarisation, presented to users in a front end web application.

Legion provides a chatbot interface to users for translating input code (for example T-SQL to Databricks SQL) and summarising the intent and business purpose of the code. This intent is then embedded for serving in a Vector Search index for finding similar pieces of code. This presents an opportunity for increased collaboration (find out who is working on similar projects), rationalisation (identify duplicates based on intent) and discoverability (semantic search).

Legion is a solution accelerator - it is *not* a fully baked solution. This is something for a customer to take on and own. This allows the customer to upskill their employees, leverage GenAI for a real use case, customise the application to their needs and entirely own the IP.
