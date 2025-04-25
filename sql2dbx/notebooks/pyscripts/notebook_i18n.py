from enum import Enum
from typing import Dict


class MessageKey(Enum):
    """Enum representing all possible message keys used in the application."""
    NOTEBOOK_DESCRIPTION = "notebook_description"
    SOURCE_SCRIPT = "source_script"
    SYNTAX_CHECK_RESULTS = "syntax_check_results"
    ERRORS_FROM_CHECKS = "errors_from_checks"
    PYTHON_SYNTAX_ERRORS = "python_syntax_errors"
    SPARK_SQL_SYNTAX_ERRORS = "spark_sql_syntax_errors"
    NO_ERRORS_DETECTED = "no_errors_detected"
    REVIEW_CODE = "review_code"


# English messages
MESSAGES_EN = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "This notebook was automatically converted from the script below. "
        "It may contain errors, so use it as a starting point and make necessary corrections."
    ),
    MessageKey.SOURCE_SCRIPT: "Source script",
    MessageKey.SYNTAX_CHECK_RESULTS: "Static Syntax Check Results",
    MessageKey.ERRORS_FROM_CHECKS: (
        "These are errors from static syntax checks. Manual corrections are required for these errors."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Python Syntax Errors",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Spark SQL Syntax Errors",
    MessageKey.NO_ERRORS_DETECTED: "No syntax errors were detected during the static check.",
    MessageKey.REVIEW_CODE: (
        "However, please review the code carefully as some issues may only be detected during runtime."
    ),
}

# Japanese messages
MESSAGES_JA = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "このノートブックは以下のスクリプトから自動的に変換されました。"
        "エラーが含まれている可能性があるため、出発点として使用し、必要な修正を行ってください。"
    ),
    MessageKey.SOURCE_SCRIPT: "ソーススクリプト",
    MessageKey.SYNTAX_CHECK_RESULTS: "静的構文チェック結果",
    MessageKey.ERRORS_FROM_CHECKS: (
        "以下は静的構文チェックの結果です。エラーがある場合、手動での修正が必要です。"
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Python構文エラー",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Spark SQL構文エラー",
    MessageKey.NO_ERRORS_DETECTED: "静的チェック中に構文エラーは検出されませんでした。",
    MessageKey.REVIEW_CODE: (
        "ただし、一部の問題は実行時にのみ検出される可能性があるため、"
        "コードを注意深く確認してください。"
    ),
}

# Chinese messages
MESSAGES_ZH = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "此笔记本是从以下脚本自动转换而来。它可能包含错误，请将其作为起点并进行必要的修正。"
    ),
    MessageKey.SOURCE_SCRIPT: "源脚本",
    MessageKey.SYNTAX_CHECK_RESULTS: "静态语法检查结果",
    MessageKey.ERRORS_FROM_CHECKS: (
        "这些是静态语法检查中发现的错误。这些错误需要手动修正。"
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Python语法错误",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Spark SQL语法错误",
    MessageKey.NO_ERRORS_DETECTED: "在静态检查中未检测到语法错误。",
    MessageKey.REVIEW_CODE: (
        "但是，请仔细检查代码，因为某些问题可能只有在运行时才能检测到。"
    ),
}

# French messages
MESSAGES_FR = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "Ce notebook a été automatiquement converti à partir du script ci-dessous. "
        "Il peut contenir des erreurs, utilisez-le comme point de départ et apportez les corrections nécessaires."
    ),
    MessageKey.SOURCE_SCRIPT: "Script source",
    MessageKey.SYNTAX_CHECK_RESULTS: "Résultats de la vérification syntaxique statique",
    MessageKey.ERRORS_FROM_CHECKS: (
        "Voici les erreurs détectées lors des vérifications syntaxiques statiques. "
        "Des corrections manuelles sont nécessaires pour ces erreurs."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Erreurs de syntaxe Python",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Erreurs de syntaxe Spark SQL",
    MessageKey.NO_ERRORS_DETECTED: "Aucune erreur de syntaxe n'a été détectée lors de la vérification statique.",
    MessageKey.REVIEW_CODE: (
        "Cependant, veuillez examiner attentivement le code car certains problèmes "
        "ne peuvent être détectés que lors de l'exécution."
    ),
}

# German messages
MESSAGES_DE = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "Dieses Notebook wurde automatisch aus dem unten stehenden Skript konvertiert. "
        "Es kann Fehler enthalten, verwenden Sie es als Ausgangspunkt und nehmen Sie die notwendigen Korrekturen vor."
    ),
    MessageKey.SOURCE_SCRIPT: "Quellskript",
    MessageKey.SYNTAX_CHECK_RESULTS: "Ergebnisse der statischen Syntaxprüfung",
    MessageKey.ERRORS_FROM_CHECKS: (
        "Dies sind Fehler aus statischen Syntaxprüfungen. "
        "Für diese Fehler sind manuelle Korrekturen erforderlich."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Python-Syntaxfehler",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Spark SQL-Syntaxfehler",
    MessageKey.NO_ERRORS_DETECTED: "Bei der statischen Prüfung wurden keine Syntaxfehler festgestellt.",
    MessageKey.REVIEW_CODE: (
        "Überprüfen Sie den Code jedoch sorgfältig, da einige Probleme "
        "möglicherweise erst zur Laufzeit erkannt werden."
    ),
}

# Italian messages
MESSAGES_IT = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "Questo notebook è stato convertito automaticamente dallo script sottostante. "
        "Potrebbe contenere errori, quindi usalo come punto di partenza e apporta le correzioni necessarie."
    ),
    MessageKey.SOURCE_SCRIPT: "Script sorgente",
    MessageKey.SYNTAX_CHECK_RESULTS: "Risultati del controllo sintattico statico",
    MessageKey.ERRORS_FROM_CHECKS: (
        "Questi sono errori derivanti dai controlli sintattici statici. "
        "Sono necessarie correzioni manuali per questi errori."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Errori di sintassi Python",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Errori di sintassi Spark SQL",
    MessageKey.NO_ERRORS_DETECTED: "Non sono stati rilevati errori di sintassi durante il controllo statico.",
    MessageKey.REVIEW_CODE: (
        "Tuttavia, si prega di rivedere attentamente il codice poiché alcuni problemi "
        "potrebbero essere rilevati solo durante l'esecuzione."
    ),
}

# Korean messages
MESSAGES_KO = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "이 노트북은 아래 스크립트에서 자동으로 변환되었습니다. "
        "오류가 포함되어 있을 수 있으므로 시작점으로 사용하고 필요한 수정을 하십시오."
    ),
    MessageKey.SOURCE_SCRIPT: "소스 스크립트",
    MessageKey.SYNTAX_CHECK_RESULTS: "정적 구문 검사 결과",
    MessageKey.ERRORS_FROM_CHECKS: (
        "이것들은 정적 구문 검사에서 발견된 오류입니다. 이러한 오류에는 수동 수정이 필요합니다."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Python 구문 오류",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Spark SQL 구문 오류",
    MessageKey.NO_ERRORS_DETECTED: "정적 검사 중 구문 오류가 감지되지 않았습니다.",
    MessageKey.REVIEW_CODE: (
        "그러나 일부 문제는 런타임에만 감지될 수 있으므로 코드를 주의 깊게 검토하십시오."
    ),
}

# Portuguese messages
MESSAGES_PT = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "Este notebook foi convertido automaticamente do script abaixo. "
        "Pode conter erros, então use-o como ponto de partida e faça as correções necessárias."
    ),
    MessageKey.SOURCE_SCRIPT: "Script fonte",
    MessageKey.SYNTAX_CHECK_RESULTS: "Resultados da verificação de sintaxe estática",
    MessageKey.ERRORS_FROM_CHECKS: (
        "Estes são erros de verificações de sintaxe estática. "
        "Correções manuais são necessárias para esses erros."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Erros de sintaxe Python",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Erros de sintaxe Spark SQL",
    MessageKey.NO_ERRORS_DETECTED: "Nenhum erro de sintaxe foi detectado durante a verificação estática.",
    MessageKey.REVIEW_CODE: (
        "No entanto, revise o código cuidadosamente, pois alguns problemas "
        "podem ser detectados apenas durante a execução."
    ),
}

# Spanish messages
MESSAGES_ES = {
    MessageKey.NOTEBOOK_DESCRIPTION: (
        "Este notebook se convirtió automáticamente del script a continuación. "
        "Puede contener errores, así que úselo como punto de partida y realice las correcciones necesarias."
    ),
    MessageKey.SOURCE_SCRIPT: "Script fuente",
    MessageKey.SYNTAX_CHECK_RESULTS: "Resultados de la comprobación de sintaxis estática",
    MessageKey.ERRORS_FROM_CHECKS: (
        "Estos son errores de las comprobaciones de sintaxis estáticas. "
        "Se requieren correcciones manuales para estos errores."
    ),
    MessageKey.PYTHON_SYNTAX_ERRORS: "Errores de sintaxis de Python",
    MessageKey.SPARK_SQL_SYNTAX_ERRORS: "Errores de sintaxis de Spark SQL",
    MessageKey.NO_ERRORS_DETECTED: "No se detectaron errores de sintaxis durante la comprobación estática.",
    MessageKey.REVIEW_CODE: (
        "Sin embargo, revise cuidadosamente el código, ya que algunos problemas "
        "solo pueden detectarse durante la ejecución."
    ),
}

# Map of language codes to message dictionaries
LANGUAGE_MAP = {
    "English": MESSAGES_EN,
    "Japanese": MESSAGES_JA,
    "Chinese": MESSAGES_ZH,
    "French": MESSAGES_FR,
    "German": MESSAGES_DE,
    "Italian": MESSAGES_IT,
    "Korean": MESSAGES_KO,
    "Portuguese": MESSAGES_PT,
    "Spanish": MESSAGES_ES,
}


def get_supported_languages() -> list[str]:
    """
    Returns a list of supported language codes.

    Returns:
        list[str]: List of supported language codes (e.g., ["English", "Japanese"])
    """
    return list(LANGUAGE_MAP.keys())


def get_language_messages(lang_code: str) -> Dict[MessageKey, str]:
    """
    Returns the message dictionary for the specified language code.
    Falls back to English if the language code is not supported.

    Args:
        lang_code (str): The language code to get messages for

    Returns:
        Dict[MessageKey, str]: Dictionary mapping message keys to translated strings
    """
    return LANGUAGE_MAP.get(lang_code, MESSAGES_EN)
