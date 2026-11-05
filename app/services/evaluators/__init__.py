from app.services.evaluators import json_eval, keyword_eval, llm_judge

EVALUATORS = {
    "keyword": keyword_eval,
    "json_schema": json_eval,
    "llm_judge": llm_judge,
}
