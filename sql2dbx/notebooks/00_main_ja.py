# Databricks notebook source
# MAGIC %md
# MAGIC # sql2dbx
# MAGIC sql2dbxは、SQLファイルをDatabricksノートブックへ変換する作業を自動化するツールです。大規模言語モデル（LLM）を活用し、各SQL方言用のシステムプロンプトに基づいて変換を行います。sql2dbxは、一連のDatabricksノートブックから構成されています。
# MAGIC
# MAGIC sql2dbxによって生成されたDatabricksノートブックは、手動での調整が必要な場合がありますが、SQLベースの処理フローをDatabricks環境に移行する際の有用な出発点となります。
# MAGIC
# MAGIC このメインノートブックは、SQLファイルをDatabricksノートブックに変換するsql2dbxの一連のプロセスのエントリーポイントとして機能します。

# COMMAND ----------

# MAGIC
# MAGIC %md-sandbox
# MAGIC ## 💫 変換フロー図
# MAGIC 以下の図は、SQLファイル群をDatabricksノートブック群に変換するプロセスの流れを表します。
# MAGIC
# MAGIC     <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
# MAGIC     <script>
# MAGIC         mermaid.initialize({startOnLoad:true});
# MAGIC     </script>
# MAGIC     <div class="mermaid">
# MAGIC       flowchart TD
# MAGIC           input[SQLファイル群] -->|Input| analyze[[01_analyze_input_files]]
# MAGIC           analyze <-->|Read & Write| conversionTable[変換結果テーブル]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| convert[[02_convert_sql_to_databricks]]
# MAGIC           convert -.->|Use| endpoint[モデルサービングエンドポイント]
# MAGIC           convert -.->|Refer| prompts["変換プロンプト YAML<br/>(SQL方言固有)"]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| validate[[03_01_static_syntax_check]]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| fixErrors[[03_02_fix_syntax_error]]
# MAGIC           fixErrors -.->|Use| endpoint
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| splitCells[[04_split_cells]]
# MAGIC
# MAGIC           conversionTable -->|Input| export[[05_export_to_databricks_notebooks]]
# MAGIC           export -->|Output| notebooks[Databricksノートブック群]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| adjust[[11_adjust_conversion_targets]]
# MAGIC
# MAGIC           %% Layout control with invisible lines
# MAGIC           convert --- validate --- fixErrors --- splitCells --- export
# MAGIC
# MAGIC           %% Styling
# MAGIC           classDef process fill:#E6E6FA,stroke:#333,stroke-width:2px;
# MAGIC           class analyze,convert,validate,fixErrors,splitCells,adjust,export process;
# MAGIC           classDef data fill:#E0F0E0,stroke:#333,stroke-width:2px;
# MAGIC           class input,conversionTable,notebooks data;
# MAGIC           classDef external fill:#FFF0DB,stroke:#333,stroke-width:2px;
# MAGIC           class endpoint,prompts external;
# MAGIC
# MAGIC           %% Make layout control lines invisible
# MAGIC           linkStyle 12 stroke-width:0px;
# MAGIC           linkStyle 13 stroke-width:0px;
# MAGIC           linkStyle 14 stroke-width:0px;
# MAGIC           linkStyle 15 stroke-width:0px;
# MAGIC     </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📝 変換ステップ
# MAGIC メインノートブックは、以下のノートブックを順番に実行します:
# MAGIC
# MAGIC | ノートブック名 | 説明 |
# MAGIC |---|---|
# MAGIC | <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a> | 入力SQLファイルの分析とトークン数の計算を行い、結果をDeltaテーブルに保存します。 |
# MAGIC | <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a> | LLMを使用してSQLコードをDatabricksノートブックで実行可能なPython関数に変換し、結果テーブルを更新します。 |
# MAGIC | <a href="$./03_01_static_syntax_check" target="_blank">03_01_static_syntax_check</a> | Python関数とその中のSpark SQLの静的構文チェックを行い、検出されたエラーを結果テーブルに更新します。 |
# MAGIC | <a href="$./03_02_fix_syntax_error" target="_blank">03_02_fix_syntax_error</a> | 前のステップで検出されたPython関数とSQL文の構文エラーをLLMを使用して修正し、結果テーブルを更新します。 |
# MAGIC | <a href="$./04_split_cells" target="_blank">04_split_cells</a> | 変換されたコードを、Databricksノートブック内での可読性や整理を高めるため、複数のセルに分割します。 |
# MAGIC | <a href="$./05_export_to_databricks_notebooks" target="_blank">05_export_to_databricks_notebooks</a> | 変換されたコードをDatabricksノートブックにエクスポートします。 |
# MAGIC | <a href="$./11_adjust_conversion_targets" target="_blank">11_adjust_conversion_targets</a> | （オプション）特定のファイルを再変換したい場合に、`is_conversion_target`を`True`に設定することで変換対象を再指定します。 |
# MAGIC
# MAGIC ## 🎯 変換対象
# MAGIC sql2dbxは、YAMLファイルで定義された変換プロンプトを使用して、様々なSQL方言からDatabricksノートブックへの変換を行います。以下の表は、各対応SQL方言のデフォルトYAMLパスを示しています。`sql_dialect`ウィジェットで特定の方言を選択すると、対応するデフォルトのYAMLファイルが自動的に使用されます。`conversion_prompt_yaml`ウィジェットでパスを指定した場合、SQL方言のデフォルトYAMLより優先されます。
# MAGIC
# MAGIC | SQL方言 | ソースシステム例 | デフォルトのYAMLファイル |
# MAGIC | --- | --- | --- |
# MAGIC | `mysql` | MySQL / MariaDB / Amazon Aurora MySQL | <a href="$./pyscripts/conversion_prompt_yaml/mysql_to_databricks_notebook.yml" target="_blank">mysql_to_databricks_notebook.yml</a> |
# MAGIC | `netezza` | IBM Netezza | <a href="$./pyscripts/conversion_prompt_yaml/netezza_to_databricks_notebook.yml" target="_blank">netezza_to_databricks_notebook.yml</a> |
# MAGIC | `oracle` | Oracle Database / Oracle Exadata | <a href="$./pyscripts/conversion_prompt_yaml/oracle_to_databricks_notebook.yml" target="_blank">oracle_to_databricks_notebook.yml</a> |
# MAGIC | `postgresql` | PostgreSQL / Amazon Aurora PostgreSQL | <a href="$./pyscripts/conversion_prompt_yaml/postgresql_to_databricks_notebook.yml" target="_blank">postgresql_to_databricks_notebook.yml</a> |
# MAGIC | `redshift` | Amazon Redshift | <a href="$./pyscripts/conversion_prompt_yaml/redshift_to_databricks_notebook.yml" target="_blank">redshift_to_databricks_notebook.yml</a> |
# MAGIC | `snowflake` | Snowflake | <a href="$./pyscripts/conversion_prompt_yaml/snowflake_to_databricks_notebook.yml" target="_blank">snowflake_to_databricks_notebook.yml</a> |
# MAGIC | `teradata` | Teradata | <a href="$./pyscripts/conversion_prompt_yaml/teradata_to_databricks_notebook.yml" target="_blank">teradata_to_databricks_notebook.yml</a> |
# MAGIC | `tsql` | Azure Synapse Analytics / Microsoft SQL Server / Azure SQL Database / Azure SQL Managed Instance | <a href="$./pyscripts/conversion_prompt_yaml/tsql_to_databricks_notebook.yml" target="_blank">tsql_to_databricks_notebook.yml</a> |
# MAGIC
# MAGIC ### カスタム変換プロンプトの作成 (オプション)
# MAGIC カスタムの変換プロンプトを作成したい場合、YAMLファイルを構造化されたフォーマットで作成し、Databricksワークスペースに配置し、`conversion_prompt_yaml`ウィジェットでフルパスを指定します。これにより、LLMは指定されたYAMLファイルを参照して変換を行います。カスタム変換プロンプトには以下の2つのセクションが必要です。
# MAGIC 
# MAGIC 1. **`system_message`**: LLMに変換方法を指示する必須セクション
# MAGIC 2. **`few_shots`**: 具体的な入出力例を示すセクション (任意だが推奨)
# MAGIC 
# MAGIC #### カスタム変換プロンプトのTips
# MAGIC 効果的な変換プロンプトを作成するためのポイントは以下の通りです。
# MAGIC 
# MAGIC **`system_message`** に含めるべき要素：
# MAGIC - 変換目的の明確な説明
# MAGIC - 入力と出力の形式の定義
# MAGIC - 特定の変換に必要な追加の指示
# MAGIC - (任意だが推奨) コメント言語の指定 (`{comment_lang}`は指定された言語に自動置換されます)
# MAGIC - (任意だが推奨) SQLからDatabricksノートブック (Python) への<a href="$./pyscripts/conversion_prompt_yaml/common_instructions/sql_to_databricks_notebook_common_python.yml" target="_blank">共通的なインストラクション</a> (`${common_python_instructions_and_guidelines}`) の参照
# MAGIC
# MAGIC **`few_shots`** の効果的な使い方：
# MAGIC - 単純な例から複雑な例まで、典型的なケースを含める
# MAGIC - 各例がLLMの理解を助ける特定のパターンを示すようにする
# MAGIC
# MAGIC #### カスタム変換プロンプトの例
# MAGIC 以下はカスタム変換プロンプト用YAMLファイルの基本的な例です。
# MAGIC
# MAGIC ```yaml
# MAGIC system_message: |
# MAGIC   Convert SQL code to Python code that runs on Databricks according to the following instructions:
# MAGIC
# MAGIC   # Input and Output
# MAGIC   - Input: A single SQL file containing one or multiple T-SQL statements (including but not limited to `CREATE OR ALTER PROCEDURE` statements).
# MAGIC   - Output: Python code with Python comments (in {comment_lang}) explaining the code and any necessary context.
# MAGIC
# MAGIC   ${common_python_instructions_and_guidelines}
# MAGIC
# MAGIC   # Additional Instructions
# MAGIC   1. Convert SQL queries to spark.sql() format
# MAGIC   2. Add clear Python comments explaining the code
# MAGIC   3. Use DataFrame operations instead of loops when possible
# MAGIC   4. Handle errors using try-except blocks
# MAGIC
# MAGIC few_shots:
# MAGIC - role: user
# MAGIC   content: |
# MAGIC     SELECT name, age
# MAGIC     FROM users
# MAGIC     WHERE active = 1;
# MAGIC - role: assistant
# MAGIC   content: |
# MAGIC     # Get names and ages of active users
# MAGIC     active_users = spark.sql("""
# MAGIC         SELECT name, age
# MAGIC         FROM users
# MAGIC         WHERE active = 1
# MAGIC     """)
# MAGIC     display(active_users)
# MAGIC ```
# MAGIC
# MAGIC ## 📢 前提条件
# MAGIC メインノートブックを実行する前に、Databricksモデルサービングエンドポイントが利用可能であることを確認してください。以下のいずれかのオプションがあります：
# MAGIC
# MAGIC 1. Databricks基盤モデルAPIを使用します（最も簡単なセットアップのため推奨）
# MAGIC 2. 外部モデルサービングエンドポイントをセットアップします。手動で設定するか、次の自動化ノートブックを使用できます：
# MAGIC     - <a href="$./external_model/external_model_azure_openai" target="_blank">Azure OpenAI Serviceエンドポイントセットアップ用ノートブック</a>
# MAGIC     - <a href="$./external_model/external_model_amazon_bedrock" target="_blank">Amazon Bedrockエンドポイントセットアップ用ノートブック</a>
# MAGIC
# MAGIC ## ❗ 重要な注意事項
# MAGIC メインノートブックを実行する前に、以下の点を考慮してください：
# MAGIC
# MAGIC ### モデルの互換性
# MAGIC sql2dbxは、大きなコンテキストウィンドウとSQL推論能力の強いモデルに最適化されています。以下のモデルは高精度な変換を行うことが確認されています：
# MAGIC
# MAGIC > **注意:** モデルの仕様は日々進化しています。実装前に、各モデルの公式ドキュメントで最新情報を確認してください。
# MAGIC
# MAGIC #### 主な推奨モデル
# MAGIC 最小限のセットアップで最適なパフォーマンスを得るために、以下のモデルを推奨します：
# MAGIC
# MAGIC | モデル | APIモデルバージョン | 入力コンテキスト | 最大出力 | セットアップ要件 | 備考 |
# MAGIC |---|---|---|---|---|---|
# MAGIC | [Claude 3.7 Sonnet](https://docs.anthropic.com/en/docs/about-claude/models/all-models) | claude-3-7-sonnet-20250219 | 200Kトークン | 通常: 8,192トークン<br>拡張思考: 64,000トークン | 基盤モデルAPIを通じてすぐに使用可能 | 複雑なSQL変換に最適な選択肢 |
# MAGIC
# MAGIC ##### 拡張思考モード
# MAGIC Claude 3.7 Sonnetの拡張思考モードは、単純なSQLクエリでは任意ですが、複雑なSQL変換の処理に推奨されます。この機能を有効にするには、以下のように思考パラメータを使用して`request_params`ノートブックウィジェットを設定します：
# MAGIC
# MAGIC 例：
# MAGIC ```json
# MAGIC {"max_tokens": 64000, "thinking": {"type": "enabled", "budget_tokens": 16000}}
# MAGIC ```
# MAGIC
# MAGIC > **注意:** 拡張思考モードを有効にすることで、複雑なSQLの変換精度が大幅に向上しますが、トークンの使用量と処理時間が増加します。入力となるSQLファイルのトークン数（SQLコメントと余分な空白を削除した後）が8,000以下の場合、拡張思考モードは安定した動作が期待できます。それ以上のトークン数ではエラーが発生する可能性があります。大規模なSQLファイルを処理する場合、小さなファイルに分割するか、拡張思考モードを使用せずに変換を行うことをお勧めします。
# MAGIC
# MAGIC #### Azure環境向けの代替オプション
# MAGIC 一部の組織では、企業ポリシーや既存のAzureへの投資など、特定の理由からAzure OpenAIモデルを使用する必要がある場合があります。そのような場合、以下のモデルが利用可能です：
# MAGIC
# MAGIC | モデル | APIモデルバージョン | 入力コンテキスト | 最大出力 | セットアップ要件 | 備考 |
# MAGIC |---|---|---|---|---|---|
# MAGIC | [Azure OpenAI o1](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/reasoning) | 2024-12-17 | 200Kトークン | 100Kトークン | 外部モデルのセットアップが必要 | Azure環境に適したオプション |
# MAGIC | [Azure OpenAI o3-mini](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/reasoning) | 2025-01-31 | 200Kトークン | 100Kトークン | 外部モデルのセットアップが必要 | Azure環境に適したオプション |
# MAGIC
# MAGIC ##### OpenAI O-seriesモデルのパラメータに関する考慮事項
# MAGIC `request_params`を指定する際には、いくつかの重要な考慮事項があります：
# MAGIC
# MAGIC 1. `reasoning_effort`パラメータ：
# MAGIC    - `reasoning_effort`は、O-seriesモデルの推論プロセスにおける思考の深さを制御します
# MAGIC    - `request_param`に`{"reasoning_effort": "high"}`のように指定することで、モデルはより深い思考を行い、複雑なSQLクエリをより正確に変換します
# MAGIC    - トレードオフとして、消費トークン数および処理時間が増加します
# MAGIC 1. トークン制限パラメータの違い：
# MAGIC    - O-seriesモデルでは`max_tokens`の使用は推奨されず、`max_completion_tokens`が使用されます
# MAGIC    - sql2dbxはトークンを制限せずに実行した方が安定した動作をするため、`max_completion_tokens`を指定せずに実行することをお勧めします
# MAGIC 1. サポートされていないパラメータ：
# MAGIC    - `temperature`や`top_p`などの生成パラメータは、O-seriesモデルではサポートされていません
# MAGIC    - 詳細については[公式ドキュメント](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/reasoning)を参照してください
# MAGIC
# MAGIC #### その他の互換性のあるモデル
# MAGIC 以下のモデルもsql2dbxで動作することが確認されており、さまざまなパフォーマンス特性があります：
# MAGIC
# MAGIC | モデル | APIモデルバージョン | 入力コンテキスト | 最大出力 | セットアップ要件 | 備考 |
# MAGIC |---|---|---|---|---|---|
# MAGIC | [Claude 3.5 Sonnet](https://docs.anthropic.com/en/docs/about-claude/models/all-models) | claude-3-5-sonnet-20241022 | 200Kトークン | 8,192トークン | 外部モデルのセットアップが必要 | 互換性を確認済み |
# MAGIC | [Azure OpenAI GPT-4o](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) | 2024-05-13 | 128Kトークン | 4,096トークン | 外部モデルのセットアップが必要 | 互換性を確認済み |
# MAGIC | [Meta Llama 3.3 70B Instruct](https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md) | llama-3-3-70b-instruct | 128Kトークン | 8,192トークン | 基盤モデルAPIを通じてすぐに使用可能 | 互換性を確認済み |
# MAGIC
# MAGIC ### SQL変換のためのトークン管理
# MAGIC 入力となるSQLファイルのトークン数は変換プロセスに直接影響します。考慮すべき2つの重要な要素は次の通りです：
# MAGIC
# MAGIC 1. 入力となるSQLファイルのトークン数よりも生成されるDatabricksノートブックのトークン数の方が通常大きくなります。入力SQLファイルはコメントを除去し複数のスペースを1つにまとめることでトークン数を削減していますが、生成結果のノートブックはコメントやインデントを含むためです
# MAGIC 2. 処理内容が多いSQLファイルの場合、一回の出力でノートブックを生成し切れない場合があります。その場合、生成済みの内容を保持しつつ、続きを段階的に出力する形になります
# MAGIC
# MAGIC これらの要因を考慮し、トークンの使用を効率的に管理することが重要です。モデルの処理可能な容量を超えるファイルは変換に失敗する可能性があるため、`token_count_threshold`パラメータで適切な閾値を設定することで、変換の成功率を高めることができます。
# MAGIC
# MAGIC #### `token_count_threshold`パラメータの推奨トークン閾値
# MAGIC `token_count_threshold`パラメータは、トークン数（ファイルサイズではなく）に基づいて処理するSQLファイルを決定します。SQLコンテンツは、SQLコメントと余分な空白を削除した後にトークン化されます。
# MAGIC
# MAGIC | モデル | 推奨`token_count_threshold` |
# MAGIC |---|---|
# MAGIC | Claude 3.7 Sonnet（通常モード） | 20,000トークン（デフォルト） |
# MAGIC | Claude 3.7 Sonnet（拡張思考モード） | 8,000トークン |
# MAGIC
# MAGIC - 通常モードの20,000トークンという値は、実際のテスト結果に基づいて設定されています。テスト環境では最大60,000トークンまでの処理に成功した例もありますが、20,000トークンを超えると処理の安定性が低下することが確認されています。最も安定した動作を得るために、20,000トークンをデフォルト値として設定しています。
# MAGIC - 他のモデル（o1、o3-miniなど）も同様に、20,000トークン程度までは比較的安定して動作することが確認されています。理論上はさらに大きな値も処理可能と考えられますが、実際の環境でテストすることをお勧めします。
# MAGIC - 拡張思考モードの8,000トークンという制限も同様に、実際のテスト結果から導き出されたものです。この値を超えるとエラーが発生したり、結果が返ってこなかったりする場合があります。大規模なSQLファイルを処理する際は、より小さな論理的なセクションに分割することをお勧めします。
# MAGIC
# MAGIC #### 入力ファイルのトークン数処理
# MAGIC <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックは、以下の手順で入力ファイルのトークン数を計算します：
# MAGIC
# MAGIC 1. エンドポイント名または明示的なトークナイザー設定に基づいて適切なトークナイザーを決定します：
# MAGIC    - Claudeモデルの場合：[Anthropicのドキュメント](https://docs.anthropic.com/en/docs/about-claude/models/all-models)に基づき、文字ベースの推定（約3.4文字/トークン）を使用
# MAGIC    - OpenAIやその他のモデルの場合：[openai/tiktoken](https://github.com/openai/tiktoken)ライブラリと適切なエンコーディングを使用
# MAGIC 2. SQLコメントと余分な空白を削除した後、選択したトークナイザーを使用して各SQLファイルのトークン数を測定します
# MAGIC 3. トークン数が`token_count_threshold`以下のファイルは変換対象としてマークされます（`is_conversion_target = True`）
# MAGIC 4. 閾値を超えるファイルは変換プロセスから除外されます
# MAGIC
# MAGIC ## 🔌 パラメーター
# MAGIC メインノートブックには以下のパラメーターの設定が必要です。より詳細な設定が必要な場合は、このメインノートブックではなく、個別のノートブックを実行してください。個別のノートブックでは、特定のタスクに対してより詳細なカスタマイズが可能です。
# MAGIC
# MAGIC 番号 (ID) | パラメーター名 | 必須 | 説明 | デフォルト値
# MAGIC --- | --- | --- | --- | ---
# MAGIC 1-1 | `input_dir` | Yes | 変換対象のSQLファイル群を格納しているディレクトリ。Pythonの`os`モジュールでアクセス可能な場所をサポート（例：Unity Catalog Volume、Workspace、Reposなど）。 |
# MAGIC 1-2 | `endpoint_name` | Yes | Databricksモデルサービングエンドポイントの名前。「Serving」タブの下でエンドポイント名を確認できます。例：エンドポイントURLが`https://<workspace_url>/serving-endpoints/hinak-oneenvgpt4o/invocations`の場合、`hinak-oneenvgpt4o`を指定します。 | `databricks-claude-3-7-sonnet`
# MAGIC 1-3 | `result_catalog` | Yes | 結果テーブルを保存する既存のカタログ。 |
# MAGIC 1-4 | `result_schema` | Yes | 指定された既存のカタログ内の、結果テーブルが配置される既存のスキーマ。 |
# MAGIC 1-5 | `token_count_threshold` | Yes | 変換プロセスに含める対象となるファイルの、SQLコメントを除いた最大トークン数。 | `20000`
# MAGIC 1-x | `existing_result_table` | No | 分析結果の保存に使用する既存の結果テーブル。指定された場合、新しいテーブルを作成する代わりにこのテーブルが使用されます。 |
# MAGIC 2-1 | `sql_dialect` | Yes | The SQL dialect of the input files. This parameter is used to determine the appropriate conversion prompts for the SQL dialect. | `tsql`
# MAGIC 2-2 | `comment_lang` | Yes | 変換したDatabricksノートブックに追加するコメントの言語。 | `English`
# MAGIC 2-3 | `concurrency` | Yes | モデルサービングエンドポイントに送信される同時リクエストの数。 | `4`
# MAGIC 2-4 | `log_level` | Yes | バッチ推論プロセスで使用するログレベル。`INFO`は標準的なログ、`DEBUG`は詳細なデバッグ情報を出力します。 | `INFO`
# MAGIC 2-x | `request_params` | No | JSON形式の追加チャットリクエストパラメータ（例：`{"max_tokens": 8192}`）（参照：[Databricks Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request)）。空の値はモデルのデフォルトパラメーターを使用します。 |
# MAGIC 2-x | `conversion_prompt_yaml` | Yes | 変換プロンプトを含むYAMLファイルへのパス。特定のSQL方言（例：T-SQL）の変換用のシステムメッセージとfew-shot例が定義されている必要があります。 |
# MAGIC 3-1 | `max_fix_attempts` | Yes | 変換結果の構文エラーを自動修正する最大試行回数。 | `1`
# MAGIC 5-1 | `output_dir` | Yes | Databricksノートブックを保存するディレクトリ。WorkspaceまたはRepos内のパスをサポート。 |
# MAGIC
# MAGIC ## 📂 入出力
# MAGIC 変換プロセスの主な入出力は以下の通りです：
# MAGIC
# MAGIC ### 入力SQLファイル
# MAGIC 入力となるSQLファイル群を`input_files_path`ディレクトリに保存してください。<a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックは、ディレクトリとそのサブディレクトリのすべてのファイルを処理します。Python `os`モジュールを通じてアクセス可能な場所（Unity Catalog Volume、Workspace、Reposなど）をサポートしています。
# MAGIC
# MAGIC ### 変換結果ノートブック（最終出力）
# MAGIC 変換結果であるDatabricksノートブック群は<a href="$./05_export_to_databricks_notebooks" target="_blank">05_export_to_databricks_notebooks</a>ノートブックによって出力され、変換プロセスの最終出力となります。出力先としてWorkspaceまたはReposのパスをサポートしています。
# MAGIC
# MAGIC ### 変換結果テーブル（中間出力）
# MAGIC 変換結果テーブルは<a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックによって作成され、変換プロセスの後続のノートブックの入出力先として利用します。これはDelta Lakeテーブルで、入力SQLファイルの分析結果（トークン数、ファイルメタデータ、変換ステータスなど）を保存します。
# MAGIC
# MAGIC #### テーブルの命名
# MAGIC テーブル名は、ノートブックで指定されたパラメータを使用して、以下の形式で作成されます：
# MAGIC
# MAGIC `{result_catalog}.{result_schema}.{result_table_prefix}_{YYYYMMDDHHmm}`
# MAGIC
# MAGIC 例えば、`result_catalog`が"my_catalog"、`result_schema`が"my_schema"、`result_table_prefix`が"conversion_targets"、現在時刻（UTC）が2024-06-14 11:39の場合、テーブル名は以下のようになります：
# MAGIC
# MAGIC `my_catalog.my_schema.conversion_targets_202406141139`
# MAGIC
# MAGIC #### テーブルスキーマ
# MAGIC テーブルスキーマは以下の通りです：
# MAGIC
# MAGIC | カラム名 | データ型 | 説明 |
# MAGIC |---|---|---|
# MAGIC | `input_file_number` | int | 各入力ファイルの一意の整数識別子。番号付けは`1`から始まります。 |
# MAGIC | `input_file_path` | string | 入力ファイルへのフルパス。 |
# MAGIC | `input_file_encoding` | string | 検出された入力ファイルのエンコーディング（例：`UTF-8`）。 |
# MAGIC | `tokenizer_type` | string | トークン数を計算するために使用されたトークナイザーの種類（例：`claude`や`openai`）。 |
# MAGIC | `tokenizer_model` | string | トークナイザーで使用された特定のモデルやエンコーディング（例：Claudeモデル用の`claude`やOpenAIモデル用の`o200k_base`）。 |
# MAGIC | `input_file_token_count` | int | 入力ファイルの総トークン数。 |
# MAGIC | `input_file_token_count_without_sql_comments` | int | SQLコメントを除いた入力ファイルのトークン数。 |
# MAGIC | `input_file_content` | string | 入力ファイルの全内容。 |
# MAGIC | `input_file_content_without_sql_comments` | string | SQLコメントを除いた入力ファイルの内容。 |
# MAGIC | `is_conversion_target` | boolean | ファイルが変換対象かどうか（TrueまたはFalse）。`01_analyze_input_files`においてSQLコメントを除いた入力ファイルのトークン数と`token_count_threshold`との比較に基づいて決定されます。変換処理が正常に終了したら自動的に`True`から`False`に更新されます。 |
# MAGIC | `model_serving_endpoint_for_conversion` | string | 変換処理に使用したモデルサービングエンドポイントの名前。 |
# MAGIC | `model_serving_endpoint_for_fix` | string | 構文エラー修正に使用したモデルサービングエンドポイントの名前。 |
# MAGIC | `request_params_for_conversion` | string | 変換処理のリクエストパラメータ（JSON形式）。 |
# MAGIC | `request_params_for_fix` | string | 構文エラー修正のリクエストパラメータ（JSON形式）。 |
# MAGIC | `result_content` | string | 処理後のファイルの変換内容。（初期値は`null`） |
# MAGIC | `result_prompt_tokens` | int | 変換に使用されたプロンプトのトークン数。（初期値は`null`） |
# MAGIC | `result_completion_tokens` | int | モデルによって生成された完了トークン数。（初期値は`null`） |
# MAGIC | `result_total_tokens` | int | 変換に使用された合計トークン数（プロンプト + 完了）。（初期値は`null`） |
# MAGIC | `result_processing_time_seconds` | float | 変換リクエストの処理にかかった時間（秒）。（初期値は`null`） |
# MAGIC | `result_timestamp` | timestamp | `result_content`が生成または更新された時のタイムスタンプ（UTC）。（初期値は`null`） |
# MAGIC | `result_error` | string | 変換プロセス中に遭遇したエラー。（初期値は`null`） |
# MAGIC | `result_python_parse_error` | string | `ast.parse`を使用したPython関数の構文チェック中に遭遇したエラー。 |
# MAGIC | `result_extracted_sqls` | array<string> | Python関数から抽出されたSQLステートメントのリスト。（初期値は`null`） |
# MAGIC | `result_sql_parse_errors` | array<string> | `EXPLAIN sql`を使用したSQL構文チェック中に遭遇したエラー。（初期値は`null`） |
# MAGIC
# MAGIC ## 🔄 特定のファイルを再変換する方法
# MAGIC 変換結果に不満がある場合、以下の手順で特定のファイルを再変換できます：
# MAGIC
# MAGIC 1.  <a href="$./11_adjust_conversion_targets" target="_blank">11_adjust_conversion_targets</a>ノートブックを使用して、再変換したいファイルの`is_conversion_target`フィールドを`True`に設定します。
# MAGIC 2.  <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a>ノートブックおよび後続の処理を再実行します。`is_conversion_target`が`True`とマークされたファイルのみが再変換されます。
# MAGIC     - LLMの変換プロセスにさらなるランダム性を導入し、実行ごとに異なる結果を得るには、モデルがサポートしている場合は`request_params`の`temperature`を0.5以上に設定することをお勧めします。
# MAGIC
# MAGIC ## 💻 動作確認済みの環境
# MAGIC このノートブックは以下の環境で動作確認しています：
# MAGIC
# MAGIC 1. ノートブックおよびジョブ用のDatabricksサーバーレスコンピュート
# MAGIC 2. Databricksクラシックコンピュート（汎用コンピュートおよびジョブコンピュート）
# MAGIC     - 推奨設定：シングルノードクラスター、Photonは不要
# MAGIC     - 検証済みのDatabricksランタイム（DBR）バージョン
# MAGIC         - 15.3 LTS
# MAGIC         - 14.3 LTS

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. パラメーターの設定
# MAGIC 主要なパラメーターをこのセクションで設定します。他の詳細なパラメーターを変更する必要がある場合は、このノートブックではなく各ノートブックを実行してください。

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json

import pandas as pd

from pyscripts.conversion_prompt_helper import ConversionPromptHelper
from pyscripts.databricks_credentials import DatabricksCredentials
from pyscripts.notebook_i18n import get_supported_languages

# COMMAND ----------

# DBTITLE 1,Configurations
# 01_analyze_input_files用のパラメータ
dbutils.widgets.text("input_dir", "", "1-1. 入力ディレクトリ")
dbutils.widgets.text("endpoint_name", "databricks-claude-3-7-sonnet", "1-2. サービングエンドポイント名")
dbutils.widgets.text("result_catalog", "", "1-3. 結果カタログ")
dbutils.widgets.text("result_schema", "", "1-4. 結果スキーマ")
dbutils.widgets.text("token_count_threshold", "20000", "1-5. 入力トークン数の閾値")
dbutils.widgets.text("existing_result_table", "", "既存の結果テーブル（任意）")

# 02_convert_sql_to_databricks用のパラメータ
dbutils.widgets.dropdown("sql_dialect", "tsql", ConversionPromptHelper.get_supported_sql_dialects(), "2-1. SQL方言")
dbutils.widgets.dropdown("comment_lang", "Japanese", get_supported_languages(), "2-2. コメント言語")
dbutils.widgets.text("concurrency", "4", "2-3. 同時リクエスト数")
dbutils.widgets.dropdown("log_level", "INFO", ["DEBUG", "INFO"], "2-4. ログレベル")
dbutils.widgets.text("request_params", "", "チャットリクエストパラメータ（任意）")
dbutils.widgets.text("conversion_prompt_yaml", "", "変換プロンプトのYAMLパス（任意）")

# 03_syntax_check_and_fix用のパラメータ
dbutils.widgets.text("max_fix_attempts", "1", "3-1. 最大修正試行回数")

# 05_export_to_databricks_notebooks用のパラメータ
dbutils.widgets.text("output_dir", "", "5-1. 出力ディレクトリ")

# COMMAND ----------

# DBTITLE 1,Load Configurations
input_dir = dbutils.widgets.get("input_dir")
endpoint_name = dbutils.widgets.get("endpoint_name")
result_catalog = dbutils.widgets.get("result_catalog")
result_schema = dbutils.widgets.get("result_schema")
token_count_threshold = int(dbutils.widgets.get("token_count_threshold"))
existing_result_table = dbutils.widgets.get("existing_result_table")
comment_lang = dbutils.widgets.get("comment_lang")
concurrency = int(dbutils.widgets.get("concurrency"))
request_params = dbutils.widgets.get("request_params")
log_level = dbutils.widgets.get("log_level")
max_fix_attempts = int(dbutils.widgets.get("max_fix_attempts"))
output_dir = dbutils.widgets.get("output_dir")

# 使用するYAMLファイルを判断
_conversion_prompt_yaml = dbutils.widgets.get("conversion_prompt_yaml")
sql_dialect = dbutils.widgets.get("sql_dialect")

if _conversion_prompt_yaml:
    conversion_prompt_yaml = _conversion_prompt_yaml
else:
    conversion_prompt_yaml = ConversionPromptHelper.get_default_yaml_for_sql_dialect(sql_dialect)

input_dir, endpoint_name, result_catalog, result_schema, token_count_threshold, existing_result_table, conversion_prompt_yaml, comment_lang, request_params, log_level, max_fix_attempts, output_dir

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. 入力ファイルの分析
# MAGIC 入力SQLファイルの分析とトークン数の計算を行い、結果をDeltaテーブルに保存します。

# COMMAND ----------

# DBTITLE 1,Analyze Input Files
result_table = dbutils.notebook.run("01_analyze_input_files", 0, {
    "input_dir": input_dir,
    "result_catalog": result_catalog,
    "result_schema": result_schema,
    "token_count_threshold": token_count_threshold,
    "existing_result_table": existing_result_table,
})
print(f"Conversion result table: {result_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 変換対象として選択されたファイル
# MAGIC トークン閾値内のファイル：Databricksノートブックへ変換されます。

# COMMAND ----------

# DBTITLE 1,Files Selected for Conversion
spark.sql(f"""
    SELECT 
        input_file_number,
        input_file_path,
        input_file_token_count_without_sql_comments
    FROM {result_table}
    WHERE is_conversion_target = true
    ORDER BY input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### トークン閾値を超えるファイル
# MAGIC 閾値を超えるファイル：手動での確認が必要です。（より小さなファイルに分割することを検討してください）

# COMMAND ----------

# DBTITLE 1,Files Exceeding Token Threshold
spark.sql(f"""
    SELECT 
        input_file_number,
        input_file_path,
        input_file_token_count_without_sql_comments
    FROM {result_table}
    WHERE is_conversion_target = false
    ORDER BY input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. SQLからDatabricksへの変換
# MAGIC LLMを使用してSQLコードをDatabricksノートブックで実行可能なPython関数に変換し、結果テーブルを更新します。

# COMMAND ----------

# DBTITLE 1,Convert SQL to Databricks Notebooks
dbutils.notebook.run("02_convert_sql_to_databricks", 0, {
    "endpoint_name": endpoint_name,
    "result_table": result_table,
    "conversion_prompt_yaml": conversion_prompt_yaml,
    "comment_lang": comment_lang,
    "concurrency": concurrency,
    "request_params": request_params,
    "log_level": log_level,
})

# COMMAND ----------

# MAGIC %md
# MAGIC ### 正常に変換されたファイル
# MAGIC 以下の表は、Databricksノートブックに正常に変換されたファイルを示しています。

# COMMAND ----------

# DBTITLE 1,Successfully Converted Files
spark.sql(f"""
    SELECT 
        input_file_number,
        input_file_path,
        result_content,
        input_file_token_count_without_sql_comments,
        result_prompt_tokens,
        result_completion_tokens,
        result_total_tokens,
        result_timestamp
    FROM {result_table}
    WHERE is_conversion_target = false
        AND result_content IS NOT NULL
    ORDER BY input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 変換エラーのあるファイル
# MAGIC 以下の表は、変換エラーのあるファイルを示しています。

# COMMAND ----------

# DBTITLE 1,Files with Conversion Errors
spark.sql(f"""
    SELECT 
        input_file_number,
        input_file_path,
        result_error,
        result_timestamp
    FROM {result_table}
    WHERE is_conversion_target = true
        AND result_error IS NOT NULL
    ORDER BY input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 構文チェックと修正
# MAGIC Python関数とその中のSpark SQLの静的構文チェックを行い、発見されたエラーの修正を試みます。

# COMMAND ----------

# DBTITLE 1,Function for Syntax Error File Count
def get_error_file_count(result_table: str) -> int:
    """Get the count of files with syntax errors."""
    error_count = spark.sql(f"""
        SELECT COUNT(*) as error_count
        FROM {result_table}
        WHERE result_python_parse_error IS NOT NULL
        OR (result_sql_parse_errors IS NOT NULL AND size(result_sql_parse_errors) > 0)
    """).collect()[0]['error_count']
    return error_count

# COMMAND ----------

# DBTITLE 1,Check and Fix Syntax Errors
for attempt in range(max_fix_attempts):
    # Run static syntax check
    print(f"Attempt {attempt + 1} of {max_fix_attempts}")
    dbutils.notebook.run("03_01_static_syntax_check", 0, {
        "result_table": result_table,
    })

    # Check if there are any errors
    error_count = get_error_file_count(result_table)
    if error_count == 0:
        print("No syntax errors found. Exiting fix loop.")
        break

    # Run fix syntax error
    print(f"Found {error_count} files with syntax errors. Attempting to fix...")
    dbutils.notebook.run("03_02_fix_syntax_error", 0, {
        "endpoint_name": endpoint_name,
        "result_table": result_table,
        "concurrency": concurrency,
        "request_params": request_params,
        "log_level": log_level,
    })

# COMMAND ----------

# MAGIC %md
# MAGIC ### 最終構文チェック
# MAGIC すべての修正試行後に最終的な静的構文チェックを実行します。

# COMMAND ----------

# DBTITLE 1,Run Final Syntax Check
dbutils.notebook.run("03_01_static_syntax_check", 0, {
    "result_table": result_table,
})
error_count = get_error_file_count(result_table)
print(f"Found {error_count} files with syntax errors.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 構文チェック結果
# MAGIC 以下の表は、成功したチェックと失敗したチェックの両方を含む、すべてのファイルの構文チェック結果を示しています。

# COMMAND ----------

# DBTITLE 1,Syntax Check Status
spark.sql(f"""
    SELECT 
        input_file_number,
        input_file_path,
        result_content,
        CASE 
            WHEN result_python_parse_error IS NULL 
                AND (result_sql_parse_errors IS NULL OR size(result_sql_parse_errors) = 0)
            THEN 'エラー無し'
            ELSE 'エラーあり'
        END as check_status,
        result_python_parse_error,
        result_sql_parse_errors
    FROM {result_table}
    ORDER BY input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. セル分割
# MAGIC 変換されたPythonコードを、Databricksノートブック内での可読性や保守性を高めるために複数のセルに分割します。

# COMMAND ----------

# DBTITLE 1,Split Cells
dbutils.notebook.run("04_split_cells", 0, {
    "result_table": result_table,
    "log_level": log_level,
})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Databricksノートブックへのエクスポート
# MAGIC 変換されたコードをDatabricksノートブックにエクスポートします。

# COMMAND ----------

# DBTITLE 1,Export to Databricks Notebooks
export_results_json = dbutils.notebook.run("05_export_to_databricks_notebooks", 0, {
    "result_table": result_table,
    "output_dir": output_dir,
    "comment_lang": comment_lang
})

# COMMAND ----------

# MAGIC %md
# MAGIC %md
# MAGIC ### 結果の概要
# MAGIC 以下の表は、すべての入力SQLファイルの変換とエクスポートの結果を示しています。

# COMMAND ----------

# DBTITLE 1,Conversion and Export Status
# 出力先ディレクトリURLを表示
full_url = f"{DatabricksCredentials().host}#workspace{output_dir}"
displayHTML(f'<p><strong>出力先ディレクトリURL: </strong><a href="{full_url}" target="_blank">{full_url}</a></p>')

# エクスポート結果の一時ビューを作成
export_results = json.loads(export_results_json)
export_results_df = pd.DataFrame(export_results)
spark.createDataFrame(export_results_df).createOrReplaceTempView("temp_export_results")

# すべてのファイルの完全なステータスを表示
spark.sql(f"""
    SELECT 
        r.input_file_number,
        r.input_file_path,
        CASE 
            WHEN r.result_content IS NULL THEN '変換無し'
            WHEN r.result_python_parse_error IS NOT NULL OR 
                 (r.result_sql_parse_errors IS NOT NULL AND size(r.result_sql_parse_errors) > 0)
            THEN 'エラーありで変換'
            ELSE '正常に変換'
        END as conversion_status,
        CASE 
            WHEN t.output_file_path IS NOT NULL THEN '正常にエクスポート'
            ELSE 'エクスポート無し'
        END as export_status,
        t.output_file_path,
        t.parse_error_count,
        r.result_python_parse_error as python_errors,
        r.result_sql_parse_errors as sql_errors
    FROM {result_table} r
    LEFT JOIN temp_export_results t
    ON r.input_file_path = t.input_file_path
    ORDER BY r.input_file_number
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 次のステップ
# MAGIC 以上でSQLからDatabricksへのすべての変換プロセスが完了しました。変換結果は指定した出力ディレクトリにある変換済みノートブックで確認できます。これらの結果を十分に確認し、変換されたコードが要件を満たし、Databricks環境で正しく動作することを確認しましょう。
# MAGIC
# MAGIC 結果を確認する際は、特に以下のケースに注意して適切に対応してください：
# MAGIC
# MAGIC 1. `変換無し` ステータスのファイル：
# MAGIC    - これらの入力ファイルは、多くの場合トークン数の上限を超えているため処理できませんでした。
# MAGIC    - 対応：これらのファイルを小さく分割するか、LLMモデルがより大きな入力を処理できる場合は`token_count_threshold`パラメータを増やして再実行してください。
# MAGIC
# MAGIC 2. `エラーありで変換` ステータスのファイル：
# MAGIC    - 変換はされたものの、構文エラーを含んでいます。
# MAGIC    - 対応：出力ノートブック下部のエラーメッセージを確認し、変換されたノートブックで手動修正を行ってください。
# MAGIC
# MAGIC 3. `エクスポート無し` ステータスのファイル：
# MAGIC    - このステータスは稀ですが、変換後のコンテンツが大きすぎる場合に発生します。
# MAGIC    - エクスポートプロセスで`Content size exceeds 10MB limit` (コンテンツサイズが10MB制限を超えています) というメッセージが表示された場合、入力ファイルが大きすぎることを意味します。
# MAGIC    - 対応：入力SQLファイルのサイズを確認し、必要に応じて小さくしてから再度変換を試みてください。
