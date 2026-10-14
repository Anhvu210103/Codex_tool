"""Record provider-reported usage; monetary amounts are estimates, not invoices."""
import json
from datetime import datetime, timezone


def ensure_usage(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS ai_usage (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, note_id TEXT, cache_hit INTEGER NOT NULL, input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER, estimated_usd REAL, prices TEXT)')


def record_usage(connection, response, provider, model, note_id, prices, cache_hit=False):
    ensure_usage(connection)
    def count(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
    usage = response.get('usage', {}) if isinstance(response, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    if cache_hit:
        incoming = cached = outgoing = total = 0
        cost = 0.0
    else:
        incoming = count(usage.get('prompt_tokens'))
        outgoing = count(usage.get('completion_tokens'))
        details = usage.get('prompt_tokens_details', {})
        details = details if isinstance(details, dict) else {}
        cached = count(usage.get('prompt_cache_hit_tokens', details.get('cached_tokens')))
        total = count(usage.get('total_tokens'))
        if total is None and incoming is not None and outgoing is not None:
            total = incoming + outgoing
        cost = None
        if incoming is not None and outgoing is not None and cached is not None and cached <= incoming:
            input_price = prices.get('input_per_million')
            cache_price = prices.get('cached_input_per_million')
            output_price = prices.get('output_per_million')
            if input_price is not None and output_price is not None and (not cached or cache_price is not None):
                cost = ((incoming-cached)*input_price + cached*(cache_price or 0) + outgoing*output_price)/1000000
    connection.execute('INSERT INTO ai_usage (created_at,provider,model,note_id,cache_hit,input_tokens,cached_tokens,output_tokens,total_tokens,estimated_usd,prices) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (datetime.now(timezone.utc).isoformat(), provider, model, note_id, int(cache_hit), incoming, cached, outgoing, total, cost, json.dumps(prices)))
    # Usage may already be billed even when the following JSON validation fails.
    connection.commit()
