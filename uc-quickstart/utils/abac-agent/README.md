# 🛡️ ABAC Policy Assistant

An AI-powered Unity Catalog Attribute-Based Access Control (ABAC) policy generation assistant built with Databricks Agent Framework and Streamlit.

## 🚀 Features

- **Intelligent Table Analysis** - Automatically examines Unity Catalog table structures, columns, and metadata
- **ABAC Policy Generation** - Creates ROW FILTER and COLUMN MASK policy recommendations
- **Tag-Based Conditions** - Generates MATCH COLUMNS and FOR TABLES conditions using `hasTag()` and `hasTagValue()`
- **Real-time Streaming** - Provides streaming responses with tool call visualization
- **Professional UI** - Clean, Databricks-branded interface with responsive design
- **Unity Catalog Integration** - Direct integration with UC functions for metadata retrieval

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Chat UI                           │
├─────────────────────────────────────────────────────────────────┤
│                 Databricks Agent Framework                     │
├─────────────────────────────────────────────────────────────────┤
│  Unity Catalog Tools                    │  LLM Endpoint        │
│  • describe_extended_table              │  • Claude Sonnet 4   │
│  • get_table_tags                       │  • Streaming         │
│  • get_column_tags                      │  • Tool Calling      │
│  • list_row_filter_column_masking       │                      │
│  • list_uc_tables                       │                      │
├──────────────────────────────────────────┼──────────────────────┤
│            Unity Catalog Metastore                             │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Prerequisites

- Databricks workspace with Unity Catalog enabled
- Model serving endpoint with agent capabilities
- Python 3.8+
- Required Unity Catalog functions deployed

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd e2e-chatbot-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Unity Catalog functions**
   
   Deploy the following functions to your Unity Catalog:
   - `enterprise_gov.gov_admin.describe_extended_table`
   - `enterprise_gov.gov_admin.get_table_tags`
   - `enterprise_gov.gov_admin.get_column_tags`
   - `enterprise_gov.gov_admin.list_row_filter_column_masking`
   - `enterprise_gov.gov_admin.list_uc_tables`

4. **Configure environment variables**
   ```bash
   export SERVING_ENDPOINT="your-agent-endpoint-name"
   ```

## 🚀 Usage

### Local Development

```bash
streamlit run app.py
```

### Databricks Apps Deployment

1. **Create app.yaml** (already configured)
   ```yaml
   command: ["streamlit", "run", "app.py"]
   env:
     - name: STREAMLIT_BROWSER_GATHER_USAGE_STATS
       value: "false"
     - name: "SERVING_ENDPOINT"
       valueFrom: "serving-endpoint"
   ```

2. **Deploy to Databricks**
   ```bash
   databricks apps create your-app-name
   databricks apps deploy your-app-name --source-dir .
   ```

## 💬 Example Queries

Ask the assistant natural language questions about your Unity Catalog tables:

```
"Suggest ABAC policies for enterprise_gov.hr_finance.customers"

"What table-level access controls should I implement for sensitive customer data?"

"Generate tag-based ABAC policies with MATCH conditions for the customers table"

"Analyze my table schema and recommend governance policies"

"What are the recommended ABAC FOR table conditions for PII data?"
```

## 🔧 Configuration

### Agent Configuration (agent.py)

- **LLM Endpoint**: Configure in `LLM_ENDPOINT_NAME`
- **System Prompt**: Customize ABAC policy generation behavior
- **UC Tools**: Add/remove Unity Catalog functions as needed
- **Vector Search**: Optional integration for document retrieval

### UI Configuration (app.py)

- **Databricks Branding**: Colors and styling in CSS
- **Page Layout**: Streamlit page configuration
- **Chat Interface**: Message rendering and interaction flow

## 📋 Available Tools

| Tool Name | Description |
|-----------|-------------|
| `describe_extended_table` | Get detailed table schema and metadata |
| `get_table_tags` | Retrieve table-level tag information |
| `get_column_tags` | Retrieve column-level tag information |
| `list_row_filter_column_masking` | Review existing ABAC policies |
| `list_uc_tables` | Discover tables in catalogs and schemas |

## 🔐 ABAC Policy Types Supported

- **ROW FILTER** policies for row-level security
- **COLUMN MASK** policies for column-level protection
- **Tag-based conditions** using `hasTag()` and `hasTagValue()`
- **Multi-table policies** with FOR TABLES conditions
- **Principal-specific** policies with TO/EXCEPT clauses

## 📊 Example Policy Output

```sql
CREATE POLICY hide_sensitive_customers
ON SCHEMA enterprise_gov.hr_finance
COMMENT 'Hide rows with sensitive customer data from general analysts'
ROW FILTER filter_sensitive_data
TO general_analysts
FOR TABLES
WHEN hasTag('sensitivity_level')
MATCH COLUMNS
  hasTagValue('data_classification', 'sensitive') AS sensitive_col
USING COLUMNS (sensitive_col);
```

## 🔍 Troubleshooting

### Common Issues

1. **Endpoint Connection Errors**
   - Verify `SERVING_ENDPOINT` environment variable
   - Check model serving endpoint permissions
   - Ensure endpoint supports agent/chat completions

2. **Unity Catalog Function Errors**
   - Verify UC functions are deployed and accessible
   - Check function permissions (CAN_EXECUTE)
   - Validate function signatures match expected format

3. **UI Rendering Issues**
   - Clear browser cache
   - Check Streamlit version compatibility
   - Verify CSS styling in different browsers

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check Databricks documentation: [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)
- Review Unity Catalog ABAC docs: [ABAC Policies](https://docs.databricks.com/data-governance/unity-catalog/abac/)
- Open an issue in this repository

## 📚 Additional Resources

- [Databricks Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)
- [Unity Catalog ABAC Tutorial](https://docs.databricks.com/data-governance/unity-catalog/abac/tutorial)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [MLflow Agent Evaluation](https://docs.databricks.com/generative-ai/agent-evaluation/)

---

Built with ❤️ using Databricks Agent Framework
