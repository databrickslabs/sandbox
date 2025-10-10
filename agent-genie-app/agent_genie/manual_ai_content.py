# Manual content storage for each AI function type
MANUAL_AI_CONTENT = {
    "ai_analyze_sentiment": """Syntax
                        SQL
                        ai_analyze_sentiment(content)

                        Arguments
                        content: A STRING expression, the text to be analyzed.
                        Returns
                        A STRING. The value is chosen from 'positive', 'negative', 'neutral', or 'mixed'. Returns null if the sentiment cannot be detected.

                        Examples
                        SQL
                        > SELECT ai_analyze_sentiment('I am happy');
                        positive

                        > SELECT ai_analyze_sentiment('I am sad');
                        negative""",
                        
    "ai_classify": """Syntax
                        ai_classify(content, labels)

                        Arguments
                        content: A STRING expression, the text to be classified.
                        labels: An ARRAY<STRING> literal, the expected output classification labels. Must contain at least 2 elements, and no more than 20 elements.
                        Returns
                        A STRING. The value matches one of the strings provided in the labels argument. Returns null if the content cannot be classified.

                        Examples
                        SQL
                        > SELECT ai_classify("My password is leaked.", ARRAY("urgent", "not urgent"));
                        urgent

                        > SELECT
                            description,
                            ai_classify(description, ARRAY('clothing', 'shoes', 'accessories', 'furniture')) AS category
                        FROM
                            products
                        ;""",

    "ai_extract": """Syntax
                        ai_extract(content, labels)

                        Arguments
                        content: A STRING expression.
                        labels: An ARRAY<STRING> literal. Each element is a type of entity to be extracted.
                        Returns
                        A STRUCT where each field corresponds to an entity type specified in labels. Each field contains a string representing the extracted entity. If more than one candidate for any entity type is found, only one is returned.

                        If content is NULL, the result is NULL.

                        Examples
                        SQL
                        > SELECT ai_extract(
                            'John Doe lives in New York and works for Acme Corp.',
                            array('person', 'location', 'organization')
                        );
                        {"person": "John Doe", "location": "New York", "organization": "Acme Corp."}

                        > SELECT ai_extract(
                            'Send an email to jane.doe@example.com about the meeting at 10am.',
                            array('email', 'time')
                        );
                        {"email": "jane.doe@example.com", "time": "10am"}""",

    "ai_fix_grammar": """
                            Syntax
                        SQL
                        ai_fix_grammar(content)

                        Arguments
                        content: A STRING expression.
                        Returns
                        A STRING with corrected grammar.

                        If content is NULL, the result is NULL.

                        Examples
                        SQL
                        > SELECT ai_fix_grammar('This sentence have some mistake');
                        "This sentence has some mistakes"

                        > SELECT ai_fix_grammar('She dont know what to did.');
                        "She doesn't know what to do."

                        > SELECT ai_fix_grammar('He go to school every days.');
                        "He goes to school every day."
                            """,
                            
    "ai_gen": """Syntax
                            ai_gen(prompt)

                            Arguments
                            prompt: A STRING expression.
                            Returns
                            A STRING.

                            Examples
                            SQL
                            > SELECT ai_gen('Generate a concise, cheerful email title for a summer bike sale with 20% discount');
                            Summer Bike Sale: Grab Your Dream Bike at 20% Off!

                            > SELECT
                                question,
                                ai_gen(
                                'You are a teacher. Answer the students question in 50 words: ' || question
                                ) AS answer
                            FROM
                                questions
                            ;

                            """,
    "ai_mask": """Syntax
                            ai_mask(content, labels)

                            Arguments
                            content: A STRING expression.
                            labels: An ARRAY<STRING> literal. Each element represents a type of information to be masked.
                            Returns
                            A STRING where the specified information is masked.

                            If content is NULL, the result is NULL.

                            Examples
                            SQL
                            > SELECT ai_mask(
                                'John Doe lives in New York. His email is john.doe@example.com.',
                                array('person', 'email')
                            );
                            "[MASKED] lives in New York. His email is [MASKED]."

                            > SELECT ai_mask(
                                'Contact me at 555-1234 or visit us at 123 Main St.',
                                array('phone', 'address')
                            );
                            "Contact me at [MASKED] or visit at [MASKED]""",
    # "ai_parse_document": "",
    "ai_similarity": """Syntax
                            ai_similarity(expr1, expr2)

                            Arguments
                            expr1: A STRING expression.
                            expr2: A STRING expression.
                            Returns
                            A FLOAT value, representing the semantic similarity between the two input strings. The output score is relative and should only be used for ranking. Score of 1 means the two text are equal.

                            Examples
                            SQL
                            > SELECT ai_similarity('Apache Spark', 'Apache Spark');
                            1.0

                            > SELECT
                            company_name
                            FROM
                            customers
                            ORDER BY ai_similarity(company_name, 'Databricks') DESC
                            ;""",

    "ai_summarize": """Syntax
                            ai_summarize(content[, max_words])

                            Arguments
                            content: A STRING expression, the text to be summarized.
                            max_words: An optional non-negative integral numeric expression representing the best-effort target number of words in the returned summary text. The default value is 50. If set to 0, there is no word limit.
                            Returns
                            A STRING.

                            If content is NULL, the result is NULL.

                            Examples
                            SQL
                            > SELECT ai_summarize(
                                'Apache Spark is a unified analytics engine for large-scale data processing. ' ||
                                'It provides high-level APIs in Java, Scala, Python and R, and an optimized ' ||
                                'engine that supports general execution graphs. It also supports a rich set ' ||
                                'of higher-level tools including Spark SQL for SQL and structured data ' ||
                                'processing, pandas API on Spark for pandas workloads, MLlib for machine ' ||
                                'learning, GraphX for graph processing, and Structured Streaming for incremental ' ||
                                'computation and stream processing.',
                                20
                            );
                            "Apache Spark is a unified, multi-language analytics engine for large-scale data processing
                            with additional tools for SQL, machine learning, graph processing, and stream computing.""",
    "ai_translate": """Syntax
                            SQL
                            ai_translate(content, to_lang)

                            Arguments
                            content: A STRING expression, the text to be translated.
                            to_lang: A STRING expression, the target language code to translate the content to.
                            Returns
                            A STRING.

                            If content is NULL, the result is NULL.

                            Examples
                            SQL
                            > SELECT ai_translate('Hello, how are you?', 'es');
                            "Hola, ¿cómo estás?"

                            > SELECT ai_translate('La vida es un hermoso viaje.', 'en');
                            "Life is a beautiful journey.""",
    "ai_forecast": """Syntax
                                SQL

                                ai_forecast(
                                observed TABLE,
                                horizon DATE | TIMESTAMP | STRING,
                                time_col STRING,
                                value_col STRING | ARRAY<STRING>,
                                group_col STRING | ARRAY<STRING> | NULL DEFAULT NULL,
                                prediction_interval_width DOUBLE DEFAULT 0.95,
                                frequency STRING DEFAULT 'auto',
                                seed INTEGER | NULL DEFAULT NULL,
                                parameters STRING DEFAULT '{}'
                                )

                                ... (truncated for brevity in this message; keep your full content here)
                                """,
    "ai_query": """Syntax
                                To query an endpoint that serves a foundation model:

                                ai_query(endpoint, request)

                                ... (truncated for brevity in this message; keep your full content here)
                                """  # For general predictive queries
}