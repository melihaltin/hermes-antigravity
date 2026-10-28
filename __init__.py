"""Hermes Agent model provider for Google Antigravity.
Direct HTTP client to Google Cloud Code endpoints, zero CLI/daemon dependencies.
"""
from pathlib import Path
from providers import register_provider
from providers.base import ProviderProfile
from .adapter import CredentialStore, DirectClient, ENDPOINT, NATIVE_TYPE

MARKER = 'antigravity-oauth-file-managed-no-token'


def auth_handler(action, args):
    if action == 'logout':
        return False
    if action == 'status':
        try:
            cred = CredentialStore().get()
            email = cred.get('email', 'authorized user')
            project = cred.get('projectId', 'default')
            print(f'antigravity: Active Google OAuth session ({email}, project: {project}).')
        except RuntimeError:
            print('antigravity: Not logged in. Run: python login.py (or hermes auth add antigravity)')
        return True
    if action in ('add', 'login', 'setup', 'refresh'):
        if action != 'refresh':
            # Run the login flow if needed
            try:
                CredentialStore().get()
            except RuntimeError:
                from .login import main as run_login
                run_login()
        CredentialStore().get(force=(action == 'refresh'))
        from agent.credential_pool import PooledCredential, load_pool
        pool = load_pool('antigravity')
        if not pool.entries():
            pool.add_entry(PooledCredential(
                provider='antigravity',
                id='google-oauth',
                label='Google Antigravity OAuth',
                auth_type='oauth',
                priority=0,
                source='manual:antigravity-auth',
                access_token=MARKER,
                base_url=ENDPOINT
            ))
        print('antigravity: Successfully linked Google Antigravity OAuth session.')
        return True
    return False


class AntigravityProfile(ProviderProfile):
    def create_client(self, **kwargs):
        return DirectClient(**kwargs)

    def fetch_models(self, **kwargs):
        return list(self.fallback_models)


# Register both 'antigravity' and 'antigravity-pi' alias for backwards compatibility
register_provider(AntigravityProfile(
    name='antigravity',
    display_name='Google Antigravity (Direct HTTP)',
    description='Direct HTTP client to Google Antigravity/CloudCode. Zero Node.js or Pi dependencies.',
    auth_type='oauth_external',
    auth_handler=auth_handler,
    base_url=ENDPOINT,
    api_mode='chat_completions',
    fallback_models=('gemini-3.8-flash', 'claude-sonnet-4-6'),
    default_aux_model='gemini-3.8-flash',
    native_reasoning_details_type=NATIVE_TYPE,
    model_capabilities={
        m: {'supports_tools': True, 'supports_vision': False, 'supports_reasoning': False, 'context_window': 200000}
        for m in ('gemini-3.8-flash', 'claude-sonnet-4-6')
    },
))

register_provider(AntigravityProfile(
    name='antigravity-pi',
    display_name='Google Antigravity (Direct HTTP - Alias)',
    description='Compatibility alias for antigravity.',
    auth_type='oauth_external',
    auth_handler=auth_handler,
    base_url=ENDPOINT,
    api_mode='chat_completions',
    fallback_models=('gemini-3.8-flash', 'claude-sonnet-4-6'),
    default_aux_model='gemini-3.8-flash',
    native_reasoning_details_type=NATIVE_TYPE,
    model_capabilities={
        m: {'supports_tools': True, 'supports_vision': False, 'supports_reasoning': False, 'context_window': 200000}
        for m in ('gemini-3.8-flash', 'claude-sonnet-4-6')
    },
))
