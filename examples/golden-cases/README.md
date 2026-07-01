# TraceLoop CI: Golden Cases (Chinese Customer Service)

A curated dataset of 30 realistic Chinese customer service scenarios
for LLM behavioral regression testing.

## Scenario coverage

| Category               | Count | Description                          |
|------------------------|-------|--------------------------------------|
| 退款/退货 (Refund)     | 10    | Returns, refunds, shipping disputes  |
| 会员权益 (Membership)  | 8     | Points, tiers, perks, auto-renewal   |
| 订单查询 (Order)       | 7     | Tracking, payment, invoices, splits  |
| 安全/合规 (Compliance) | 5     | Fraud, privacy, counterfeits         |

## Case format

Each case has:

```json
{
  "input_text": "用户问题",
  "expected_keywords": ["LLM回复必须包含的词"],
  "forbidden_keywords": ["LLM回复不得出现的词"],
  "tags": ["场景标签"]
}
```

`expected_keywords` and `forbidden_keywords` form the evaluation criteria:
the LLM passes the test only if the response contains all expected terms
and none of the forbidden ones.

## Import

```bash
# Install httpx if you haven't
pip install httpx

# Import all 30 cases (server must be running)
python import.py
```

The script creates the dataset if it doesn't exist, then imports each
case with progress reporting and error handling.

## Customisation

- Set `TRACELOOP_URL` env var to use a different server address
- Set `TRACELOOP_DATASET` env var to use a different dataset ID
- Add more cases to the JSON file and re-run the import
