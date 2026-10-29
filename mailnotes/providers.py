"""Approved AI gateways used by the local notebook.

API keys are deliberately not kept here. They live in a private file on the
customer's machine or in the corresponding environment variable.
"""

PROVIDERS = {
    'vngcloud': {
        'label': 'GreenNode / VNG Cloud',
        'endpoint': 'https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions',
        'environment': 'VNGCLOUD_API_KEY',
        'model': 'deepseek/deepseek-v4-flash',
    },
    # Kept only so older local settings and their historical documents remain
    # readable during migration. The customer-facing setup uses VNG Cloud.
    'deepseek': {
        'label': 'DeepSeek (legacy)',
        'endpoint': 'https://api.deepseek.com/chat/completions',
        'environment': 'DEEPSEEK_API_KEY',
        'model': 'deepseek-chat',
    },
}


def provider(name):
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError('Nhà cung cấp AI không hợp lệ.') from None
