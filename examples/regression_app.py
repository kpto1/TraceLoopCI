"""Replace this adapter with your application's actual prompt/RAG entry point."""


def answer(case):
    if "退款" in case["input_text"]:
        return "支持7天内退款，参见 refund-policy。"
    return "请联系客服。"
