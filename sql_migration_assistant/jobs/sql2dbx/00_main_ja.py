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
# MAGIC           convert -.->|Use| endpoint[LLMエンドポイント]
# MAGIC           convert -.->|Refer| prompts["システムプロンプト\n(SQL方言固有)"]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| validate[[03_01_static_syntax_check]]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| fixErrors[[03_02_fix_syntax_error]]
# MAGIC           fixErrors -.->|Use| endpoint
# MAGIC
# MAGIC           conversionTable -->|Input| export[[04_export_to_databricks_notebooks]]
# MAGIC           export -->|Output| notebooks[Databricksノートブック群]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| adjust[[05_adjust_conversion_targets]]
# MAGIC
# MAGIC           %% Layout control with invisible lines
# MAGIC           convert --- validate --- fixErrors --- export
# MAGIC
# MAGIC           %% Styling
# MAGIC           classDef process fill:#E6E6FA,stroke:#333,stroke-width:2px;
# MAGIC           class analyze,convert,validate,fixErrors,adjust,export process;
# MAGIC           classDef data fill:#E0F0E0,stroke:#333,stroke-width:2px;
# MAGIC           class input,conversionTable,notebooks data;
# MAGIC           classDef external fill:#FFF0DB,stroke:#333,stroke-width:2px;
# MAGIC           class endpoint,prompts external;
# MAGIC
# MAGIC           %% Make layout control lines invisible
# MAGIC           linkStyle 11 stroke-width:0px;
# MAGIC           linkStyle 12 stroke-width:0px;
# MAGIC           linkStyle 13 stroke-width:0px;
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
# MAGIC | <a href="$./04_export_to_databricks_notebooks" target="_blank">04_export_to_databricks_notebooks</a> | 変換されたコードをDatabricksノートブックにエクスポートします。 |
# MAGIC | <a href="$./05_adjust_conversion_targets" target="_blank">05_adjust_conversion_targets</a> | （オプション）再変換が必要な特定のファイルの`is_conversion_target`フィールドを`True`に設定することで、変換対象を調整します。これは、満足に変換されなかったファイルを再処理するために使用できます。 |
# MAGIC
# MAGIC ## 🎯 変換対象
# MAGIC 現在、sql2dbxは**T-SQL**（Transact-SQL）コードからDatabricksノートブックへの変換をサポートしています。sql2dbxはLLMを用いて変換を行うため、システムプロンプトを追加することで、様々なSQL方言に対応できます。
# MAGIC
# MAGIC 今後、T-SQL以外のSQL方言のサポートを追加する予定ですが、そちらを待たずに、ユーザーが独自のシステムプロンプトを使用することもできます。ただし、これには<a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a>ノートブックの軽微な修正が必要です。
# MAGIC
# MAGIC ## 📢 前提条件
# MAGIC メインノートブックを実行する前に、外部モデルまたは基盤モデルAPIを使用したDatabricksモデルサービングエンドポイントが利用可能であることを確認してください。外部モデルサービングエンドポイントのセットアップが必要な場合は、必要に応じて以下の自動化ノートブックを使用できます：
# MAGIC
# MAGIC - <a href="$./external_model/external_model_azure_openai" target="_blank">Azure OpenAI Serviceエンドポイントセットアップ用ノートブック</a>
# MAGIC - <a href="$./external_model/external_model_amazon_bedrock" target="_blank">Amazon Bedrockエンドポイントセットアップ用ノートブック</a>
# MAGIC
# MAGIC ## ❗ 特記事項
# MAGIC メインノートブックを実行する前に、以下の点を考慮してください：
# MAGIC
# MAGIC ### モデルの互換性
# MAGIC sql2dbxは、以下の最新（state-of-the-art）モデルを用いることで、十分な入出力トークン長で高い精度の変換が可能であることを確認しています。最善の結果を得るには、以下のモデルあるいは同等以上の能力を持つモデルの使用を推奨します。他の基盤モデルでも機能すると予想されますが、特定のモデルの能力と制限に応じて、プロンプト、パラメータ、あるいはノートブックのコード自体の調整が必要になる場合があります。
# MAGIC
# MAGIC * [Anthropic Claude 3.5 Sonnet](https://www.anthropic.com/news/claude-3-5-sonnet) (200Kトークンのコンテキストウィンドウ)
# MAGIC * [OpenAI GPT-4o (Omni)](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) (128K入力トークン、4K出力トークン)
# MAGIC * [Meta Llama 3.1 405B Instruct](https://docs.databricks.com/en/machine-learning/foundation-models/supported-models.html#meta-llama-31-405b-instruct) (128Kトークンのコンテキストウィンドウ)
# MAGIC
# MAGIC ### 入力ファイルのトークン制限
# MAGIC <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックで、各SQLファイルのトークン数を計測し、Databricksノートブックへの変換対象とするかを判定します。具体的な処理の流れは以下の通りです：
# MAGIC
# MAGIC 1. 各SQLファイルのコメントを除外および複数半角スペースを1スペースに圧縮後、トークン数を計測します。トークン数の計測には[openai/tiktoken](https://github.com/openai/tiktoken)の`o200k_base`トークナイザーを使用します。
# MAGIC 2. 計測されたトークン数が`token_count_threshold`パラメーター以下の場合、そのファイルは変換対象となります。
# MAGIC     - この条件を満たすファイルは、`is_conversion_target`フィールドが`True`に設定されます。
# MAGIC 3. `token_count_threshold`を超えるファイルは処理対象外となります。
# MAGIC
# MAGIC `token_count_threshold`のデフォルト値は20,000トークンに設定しています。この値は、(Azure) OpenAIの[GPT-4o](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)のトークン制限（入力トークン制限128,000トークン、出力トークン制限4,096トークン）を考慮し、十分な安全マージンを取って設定したものです。これにより、モデルの制約を超えることなくファイルを効率的に処理できます。異なるモデルを使用する場合や、より大きなファイルを処理する必要がある場合は、使用するモデルのトークン長制限とタスクの要件に合わせて`token_count_threshold`の値を調整してください。
# MAGIC
# MAGIC ## 🔌 パラメーター
# MAGIC メインノートブックには以下のパラメーターの設定が必要です。より詳細な設定が必要な場合は、このメインノートブックではなく、個別のノートブックを実行してください。個別のノートブックでは、特定のタスクに対してより詳細なカスタマイズが可能です。
# MAGIC
# MAGIC パラメーター名 | 必須 | デフォルト値 | 説明
# MAGIC --- | --- | --- | ---
# MAGIC `input_dir` | Yes | | 変換対象のSQLファイル群を格納しているディレクトリ。Pythonの`os`モジュールでアクセス可能な場所をサポート（例：Unity Catalog Volume、Workspace、Reposなど）。
# MAGIC `result_catalog` | Yes | | 結果テーブルを保存する既存のカタログ。
# MAGIC `result_schema` | Yes | | 指定された既存のカタログ内の、結果テーブルが配置される既存のスキーマ。
# MAGIC `token_count_threshold` | Yes | `20000` | 変換プロセスに含める対象となるファイルの、SQLコメントを除いた最大トークン数。
# MAGIC `existing_result_table` | No | | 分析結果の保存に使用する既存の結果テーブル。指定された場合、新しいテーブルを作成する代わりにこのテーブルが使用されます。
# MAGIC `endpoint_name` | Yes | | Databricksモデルサービングエンドポイントの名前。
# MAGIC `sql_dialect` | Yes | `tsql` | SQL方言。現在はtsqlのみサポート。
# MAGIC `comment_lang` | Yes | `English` | 変換したDatabricksノートブックに付与するコメントの言語。英語または日本語から選択。
# MAGIC `request_params` | Yes | `{"max_tokens": 4000, "temperature": 0}` | JSON形式の追加チャットHTTPリクエストパラメータ（参照：[Databricks Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request)）。
# MAGIC `max_fix_attempts` | Yes | `1` | 変換結果の構文エラーを自動修正する最大試行回数。
# MAGIC `output_dir` | Yes | | Databricksノートブックを保存するディレクトリ。WorkspaceまたはRepos内のパスをサポート。
# MAGIC
# MAGIC ## 📂 入出力
# MAGIC 変換プロセスの主な入出力は以下の通りです：
# MAGIC
# MAGIC ### 入力SQLファイル
# MAGIC 入力となるSQLファイル群を`input_files_path`ディレクトリに保存してください。<a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックは、ディレクトリとそのサブディレクトリのすべてのファイルを処理します。Python `os`モジュールを通じてアクセス可能な場所（Unity Catalog Volume、Workspace、Reposなど）をサポートしています。
# MAGIC
# MAGIC ### 変換結果ノートブック（最終出力）
# MAGIC 変換結果であるDatabricksノートブック群は<a href="$./04_export_to_databricks_notebooks" target="_blank">04_export_to_databricks_notebooks</a>ノートブックによって出力されます。出力先としてWorkspaceまたはReposのパスをサポートしています。
# MAGIC
# MAGIC ### 変換結果テーブル（中間出力）
# MAGIC 変換結果テーブルは<a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>ノートブックによって作成され、変換プロセスの後続のノートブックの入出力先として利用します。
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
# MAGIC | `tiktoken_encoding` | string | LLMでのトークン化に使用されるエンコーディング（例：`o200k_base`）。 |
# MAGIC | `input_file_token_count` | int | 入力ファイルの総トークン数。 |
# MAGIC | `input_file_token_count_without_sql_comments` | int | SQLコメントを除いた入力ファイルのトークン数。 |
# MAGIC | `input_file_content` | string | 入力ファイルの全内容。 |
# MAGIC | `input_file_content_without_sql_comments` | string | SQLコメントを除いた入力ファイルの内容。 |
# MAGIC | `is_conversion_target` | boolean | ファイルが変換対象かどうか（TrueまたはFalse）。`01_analyze_input_files`においてSQLコメントを除いた入力ファイルのトークン数と`token_count_threshold`との比較に基づいて決定されます。変換処理が正常に終了したら自動的に`True`から`False`に更新されます。 |
# MAGIC | `model_serving_endpoint_for_conversion` | string | 変換処理に使用したモデルサービングエンドポイントの名前。 |
# MAGIC | `model_serving_endpoint_for_fix` | string | 構文エラー修正に使用したモデルサービングエンドポイントの名前。 |
# MAGIC | `result_content` | string | 処理後のファイルの変換内容。（初期値は`null`） |
# MAGIC | `result_token_count` | int | 変換された内容のトークン数。（初期値は`null`） |
# MAGIC | `result_error` | string | 変換プロセス中に遭遇したエラー。（初期値は`null`） |
# MAGIC | `result_timestamp` | string | `result_content`が生成または更新された時のタイムスタンプ（UTC）。（初期値は`null`） |
# MAGIC | `result_python_parse_error` | string | `ast.parse`を使用したPython関数の構文チェック中に遭遇したエラー。 |
# MAGIC | `result_extracted_sqls` | array<string> | Python関数から抽出されたSQLステートメントのリスト。（初期値は`null`） |
# MAGIC | `result_sql_parse_errors` | array<string> | `spark._jsparkSession.sessionState().sqlParser().parsePlan()`を使用したSQL構文チェック中に遭遇したエラー。（初期値は`null`） |
# MAGIC
# MAGIC ## 🔄 特定のファイルを再変換する方法
# MAGIC 変換結果に不満がある場合、以下の手順で特定のファイルを再変換できます：
# MAGIC
# MAGIC 1.  <a href="$./05_adjust_conversion_targets" target="_blank">05_adjust_conversion_targets</a>ノートブックを使用して、再変換したいファイルの`is_conversion_target`フィールドを`True`に設定します。
# MAGIC 2.  <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a>ノートブックを再実行します。`is_conversion_target`が`True`とマークされたファイルのみが再変換されます。
# MAGIC     - LLMの変換プロセスにさらなるランダム性を導入し、実行ごとに異なる結果を得るには、`request_params`の`temperature`を0.5以上に設定することをお勧めします。
# MAGIC
# MAGIC ## 💻 動作確認済みの環境
# MAGIC このノートブックは以下の環境で動作確認しています：
# MAGIC
# MAGIC - Databricks Runtime (DBR)
# MAGIC     - 14.3 LTS
# MAGIC     - 15.3
# MAGIC - シングルノードクラスター構成
# MAGIC     - 注意事項：サーバーレスでは動作しない処理が含まれるため、シングルノードクラスターで実行してください

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. パラメーターの設定
# MAGIC 主要なパラメーターをこのセクションで設定します。他の詳細なパラメーターを変更する必要がある場合は、このノートブックではなく各ノートブックを実行してください。

# COMMAND ----------

# DBTITLE 1,Configurations
# 01_analyze_input_files用のパラメータ
dbutils.widgets.text("input_dir", "", "入力ディレクトリ")
dbutils.widgets.text("result_catalog", "", "結果カタログ")
dbutils.widgets.text("result_schema", "", "結果スキーマ")
dbutils.widgets.text("token_count_threshold", "20000", "入力トークン数の閾値")
dbutils.widgets.text("existing_result_table", "", "既存の結果テーブル（任意）")

# 02_convert_sql_to_databricks用のパラメータ
dbutils.widgets.text("endpoint_name", "", "サービングエンドポイント名")
dbutils.widgets.dropdown("sql_dialect", "tsql", ["tsql"], "SQL方言")
dbutils.widgets.dropdown("comment_lang", "English", ["English", "Japanese"], "コメント言語")
dbutils.widgets.text("request_params", '{"max_tokens": 4000, "temperature": 0}', "チャットリクエストパラメータ")

# 03_syntax_check_and_fix用のパラメータ
dbutils.widgets.text("max_fix_attempts", "1", "最大修正試行回数")

# 04_export_to_databricks_notebooks用のパラメータ
dbutils.widgets.text("output_dir", "", "出力ディレクトリ")

# COMMAND ----------

# DBTITLE 1,Load Configurations
input_dir = dbutils.widgets.get("input_dir")
result_catalog = dbutils.widgets.get("result_catalog")
result_schema = dbutils.widgets.get("result_schema")
token_count_threshold = int(dbutils.widgets.get("token_count_threshold"))
existing_result_table = dbutils.widgets.get("existing_result_table")
endpoint_name = dbutils.widgets.get("endpoint_name")
sql_dialect = dbutils.widgets.get("sql_dialect")
comment_lang = dbutils.widgets.get("comment_lang")
request_params = dbutils.widgets.get("request_params")
max_fix_attempts = int(dbutils.widgets.get("max_fix_attempts"))
output_dir = dbutils.widgets.get("output_dir")

input_dir, result_catalog, result_schema, token_count_threshold, existing_result_table, endpoint_name, sql_dialect, comment_lang, request_params, max_fix_attempts, output_dir

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
# MAGIC ## 2. SQLからDatabricksへの変換
# MAGIC LLMを使用してSQLコードをDatabricksノートブックで実行可能なPython関数に変換し、結果テーブルを更新します。

# COMMAND ----------

# DBTITLE 1,Convert SQL to Databricks Notebooks
dbutils.notebook.run("02_convert_sql_to_databricks", 0, {
    "endpoint_name": endpoint_name,
    "result_table": result_table,
    "sql_dialect": sql_dialect,
    "comment_lang": comment_lang,
    "request_params": request_params,
})

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
        "request_params": request_params,
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
# MAGIC ## 4. Databricksノートブックへのエクスポート
# MAGIC 変換されたコードをDatabricksノートブックにエクスポートします。

# COMMAND ----------

# DBTITLE 1,Export to Databricks Notebooks
export_results_json = dbutils.notebook.run("04_export_to_databricks_notebooks", 0, {
    "result_table": result_table,
    "output_dir": output_dir
})

# COMMAND ----------

# MAGIC %md
# MAGIC ### エクスポート結果の表示
# MAGIC 以下のセルはノートブックのエクスポート結果を表示します。エクスポート結果の情報は以下の通りです。
# MAGIC
# MAGIC - `export_succeeded`: エクスポートが成功したかどうかを示すブール値
# MAGIC - `parse_error_count`: エクスポートされたノートブックに含まれる静的解析エラーの数
# MAGIC
# MAGIC `parse_error_count`が`1`以上のノートブックは静的解析エラーを含むため、マニュアルでのレビューおよび修正が必要です。

# COMMAND ----------

# DBTITLE 1,Display Export Results
import json
import pandas as pd

export_results = json.loads(export_results_json)
export_results_df = pd.DataFrame(export_results)
display(export_results_df)
