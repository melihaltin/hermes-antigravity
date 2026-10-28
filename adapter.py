"""Hermes Agent model provider for Google Antigravity.
Direct HTTP client to Google Cloud Code endpoints, zero CLI/daemon dependencies.
"""
from base64 import b64decode
import json
import os
from pathlib import Path
import re
import time
import httpx

def _default_creds():
    c1 = ('MTA3MTAwNjA2MDU5MS10bWhzc2luMmgyMWxjcmUyMzV2dG9sb2poNGc0MDNlc', 'C5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbQ==')
    c2 = ('R09DU1BYLUs1OEZXUjQ', '4NkxkTEoxbUxCOHNYQzR6NnFEQWY=')
    return b64decode(''.join(c1)).decode(), b64decode(''.join(c2)).decode()


TOKEN_URL = 'https://oauth2.googleapis.com/token'


def oauth_client():
    """Returns (client_id, client_secret) for Google OAuth."""
    explicit_id = os.environ.get('ANTIGRAVITY_CLIENT_ID')
    explicit_sec = os.environ.get('ANTIGRAVITY_CLIENT_SECRET')
    if explicit_id and explicit_sec:
        return explicit_id, explicit_sec

    # Check legacy Pi extension if present, otherwise use built-in defaults
    pi_source = Path.home() / '.pi/agent/npm/node_modules/pi-antigravity/src/auth/oauth.ts'
    if pi_source.exists():
        try:
            source = pi_source.read_text(encoding='utf-8')
            values = []
            for name in ('CLIENT_ID', 'CLIENT_SECRET'):
                block = source.split('export const ' + name + ' =', 1)[1].split(';', 1)[0]
                encoded = ''.join(re.findall(r'"([A-Za-z0-9+/=]+)"', block.split('atob(', 1)[1]))
                values.append(b64decode(encoded).decode())
            return values[0], values[1]
        except Exception:
            pass
    return _default_creds()


class CredentialStore:
    def __init__(self, path=None, http=None):
        if path:
            self.paths = [Path(path)]
        else:
            self.paths = [
                Path.home() / '.hermes/antigravity-auth.json',
                Path.home() / '.pi/agent/auth.json'
            ]
        self.http = http or httpx.Client(timeout=30, follow_redirects=False)

    def get_auth_file(self):
        for p in self.paths:
            if p.exists():
                return p
        return self.paths[0]

    def get(self, force=False):
        entry = None
        target_path = None
        for p in self.paths:
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                candidate = data.get('antigravity', data)
                if candidate.get('type') == 'oauth' and candidate.get('access') and candidate.get('projectId'):
                    entry = candidate
                    target_path = p
                    break
            except Exception:
                continue

        if not entry:
            raise RuntimeError(
                'Antigravity OAuth credentials unavailable. Please run: python login.py (or hermes auth add antigravity)'
            )

        expires = float(entry.get('expires', 0))
        if force or expires <= time.time() * 1000:
            client_id, client_secret = oauth_client()
            try:
                response = self.http.post(
                    TOKEN_URL,
                    data={
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'grant_type': 'refresh_token',
                        'refresh_token': entry['refresh']
                    },
                    follow_redirects=False
                )
                if response.status_code != 200:
                    raise RuntimeError(f'Google OAuth refresh failed (HTTP {response.status_code}); re-authenticate with python login.py.')
                data = response.json()
                entry['access'] = data['access_token']
                entry['expires'] = int(time.time() * 1000 + data.get('expires_in', 3600) * 1000 - 300000)
                # Save updated access token back
                if target_path and target_path.exists():
                    try:
                        raw = json.loads(target_path.read_text(encoding='utf-8'))
                        if 'antigravity' in raw:
                            raw['antigravity'] = entry
                        else:
                            raw = entry
                        target_path.write_text(json.dumps(raw, indent=2), encoding='utf-8')
                    except Exception:
                        pass
            except httpx.HTTPError:
                raise RuntimeError('Google OAuth refresh network error; check connection or re-run login.py.') from None

        return entry


ENDPOINT = 'https://daily-cloudcode-pa.googleapis.com'
NATIVE_TYPE = 'antigravity.native_assistant'
USER_AGENT = 'antigravity/cli/1.4.0 (aidev_client; os_type=linux; arch=amd64; cl=982146307; auth_method=consumer)'


def text_parts(content):
    if isinstance(content, str):
        return [{'text': content}] if content else []
    if isinstance(content, list):
        if any(p.get('type') not in ('text', 'input_text') for p in content):
            raise RuntimeError('antigravity currently supports text content only.')
        return [{'text': p.get('text', '')} for p in content]
    return []


def normalize_schema(schema, legacy=False):
    root = schema
    budget = [10000]

    def walk(node, seen=(), depth=0):
        budget[0] -= 1
        if depth > 64 or budget[0] < 0:
            raise RuntimeError('Tool schema expansion limit exceeded.')
        if not isinstance(node, dict):
            return node
        if '$ref' in node:
            ref = node['$ref']
            if not isinstance(ref, str) or not ref.startswith('#/') or ref in seen:
                raise RuntimeError('Tool schema has an unsupported or recursive reference.')
            target = root
            try:
                for key in ref[2:].split('/'):
                    target = target[key.replace('~1', '/').replace('~0', '~')]
            except (KeyError, TypeError):
                raise RuntimeError('Tool schema contains an unresolved reference.') from None
            return walk({**target, **{k: v for k, v in node.items() if k != '$ref'}}, seen + (ref,), depth + 1)
        out = {}
        for key, value in node.items():
            if key.startswith('$') or key == 'definitions':
                continue
            if legacy and key not in ('type', 'description', 'properties', 'required', 'items', 'enum'):
                continue
            if key == 'properties':
                out[key] = {k: walk(v, seen, depth + 1) for k, v in value.items()}
            elif key == 'items' or (key == 'additionalProperties' and isinstance(value, dict)):
                out[key] = walk(value, seen, depth + 1)
            elif key in ('anyOf', 'oneOf', 'allOf', 'prefixItems'):
                out[key] = [walk(v, seen, depth + 1) for v in value]
            elif legacy and key == 'type' and isinstance(value, list):
                out[key] = next((v for v in value if v != 'null'), 'string')
            elif legacy and key == 'enum' and not all(isinstance(v, str) for v in value):
                continue
            else:
                out[key] = value
        return out

    return walk(root)


def build_request(model, messages, project, tools=None, **kwargs):
    import hashlib
    import uuid

    contents, system, names, unsigned = [], [], {}, set()
    claude = model.startswith('claude-')

    def append(role, parts):
        if not parts:
            return
        if contents and contents[-1]['role'] == role:
            contents[-1]['parts'].extend(parts)
        else:
            contents.append({'role': role, 'parts': parts})

    for message in messages:
        role = message['role']
        if role in ('system', 'developer'):
            system.extend(text_parts(message.get('content')))
        elif role == 'tool':
            call_id = message.get('tool_call_id', '')
            response = {'name': names.get(call_id, message.get('name', 'tool')), 'response': {'output': message.get('content', '')}}
            if claude:
                response['id'] = call_id
            if call_id in unsigned:
                append('user', [{'text': '[Observation from ' + response['name'] + ': ' + str(message.get('content', '')) + ']'}])
            else:
                append('user', [{'functionResponse': response}])
        elif role == 'assistant':
            calls = message.get('tool_calls') or []
            for call in calls:
                names[call['id']] = call['function']['name']
            native = next((d for d in message.get('reasoning_details', []) if d.get('type') == NATIVE_TYPE and d.get('model') == model), None)
            if native:
                import copy
                parts = [copy.deepcopy(p) for p in native['parts'] if p.get('text') or 'text' not in p or p.get('thoughtSignature')]
            else:
                parts = text_parts(message.get('content'))
                for call in calls:
                    fn = call['function']
                    if model.startswith('gemini-3'):
                        unsigned.add(call['id'])
                        parts.append({'text': '[Previous tool call: ' + fn['name'] + ' ' + fn.get('arguments', '{}') + ']'})
                        continue
                    part = {'functionCall': {'name': fn['name'], 'args': json.loads(fn.get('arguments') or '{}')}}
                    if claude:
                        part['functionCall']['id'] = call['id']
                    parts.append(part)
            append('model', parts)
        else:
            append('user', text_parts(message.get('content')))

    config = {'maxOutputTokens': kwargs.get('max_completion_tokens') or kwargs.get('max_tokens') or 8192}
    if kwargs.get('temperature') is not None:
        config['temperature'] = kwargs['temperature']

    request = {'contents': contents, 'generationConfig': config}
    if system:
        request['systemInstruction'] = {'role': 'user', 'parts': system}
    if tools:
        declarations = []
        for tool in tools:
            fn = tool['function']
            declarations.append({
                'name': fn['name'],
                'description': fn.get('description', ''),
                'parameters' if claude else 'parametersJsonSchema': normalize_schema(
                    fn.get('parameters', {'type': 'object', 'properties': {}}), legacy=claude
                )
            })
        request['tools'] = [{'functionDeclarations': declarations}]

    choice = kwargs.get('tool_choice')
    if choice in ('required', 'none') or isinstance(choice, dict):
        calling = {'mode': 'NONE' if choice == 'none' else 'ANY'}
        if isinstance(choice, dict):
            calling['allowedFunctionNames'] = [choice['function']['name']]
        request['toolConfig'] = {'functionCallingConfig': calling}

    seed = json.dumps(messages[:1], sort_keys=True)
    trajectory = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
    step = len(contents)
    request['sessionId'] = str(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], 'little', signed=True))
    request['labels'] = {
        'last_step_index': str(max(0, step - 1)),
        'request_id': trajectory + '-' + str(sum(m['role'] == 'assistant' for m in messages)),
        'trajectory_id': trajectory,
        'used_claude': str(claude).lower(),
        'used_claude_conservative': str(claude).lower(),
        'used_non_gemini_model': str(claude).lower()
    }
    return {
        'project': project,
        'model': 'gemini-3.8-flash-low' if model == 'gemini-3.8-flash' else model,
        'request': request,
        'requestType': 'agent',
        'userAgent': 'antigravity',
        'requestId': f'agent/{trajectory}/{int(time.time() * 1000)}/{trajectory}/{max(1, step)}'
    }


class DirectClient:
    HERMES_SKIP_TRANSPORT_WRAP = True

    def __init__(self, auth_path=None, http=None, **kwargs):
        from types import SimpleNamespace
        self.http = http or httpx.Client(timeout=httpx.Timeout(180, connect=20), follow_redirects=False)
        self.store = CredentialStore(auth_path, http=self.http)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def close(self):
        self.http.close()

    def create(self, *, model, messages, tools=None, stream=False, _retried=False, **kwargs):
        from openai.types.chat import ChatCompletion
        import uuid

        credential = self.store.get(force=_retried)
        body = build_request(model, messages, credential['projectId'], tools, **kwargs)
        parts, usage, finish = [], {}, None
        try:
            with self.http.stream(
                'POST',
                ENDPOINT + '/v1internal:streamGenerateContent?alt=sse',
                json=body,
                headers={
                    'Authorization': 'Bearer ' + credential['access'],
                    'User-Agent': USER_AGENT,
                    'Content-Type': 'application/json'
                },
                follow_redirects=False
            ) as response:
                if response.status_code == 401 and not _retried:
                    response.close()
                    return self.create(model=model, messages=messages, tools=tools, stream=stream, _retried=True, **kwargs)
                if response.status_code != 200:
                    raise RuntimeError(f'Google Antigravity request failed (HTTP {response.status_code}).')
                for line in response.iter_lines():
                    if not line.startswith('data:'):
                        continue
                    raw = line[5:].strip()
                    if not raw or raw == '[DONE]':
                        continue
                    chunk = json.loads(raw)
                    if 'error' in chunk:
                        raise RuntimeError('Google Antigravity reported a stream error.')
                    data = chunk.get('response', chunk)
                    candidates = data.get('candidates') or []
                    if candidates:
                        candidate = candidates[0]
                        parts.extend(candidate.get('content', {}).get('parts', []))
                        finish = candidate.get('finishReason') or finish
                    usage = data.get('usageMetadata') or usage
        except (httpx.HTTPError, ValueError):
            raise RuntimeError('Google Antigravity transport failed.') from None

        if not finish:
            raise RuntimeError('Google Antigravity stream ended without a finish reason.')
        if finish not in ('STOP', 'MAX_TOKENS'):
            raise RuntimeError('Google Antigravity returned a blocked or unsupported finish reason.')

        calls = []
        for part in parts:
            if 'functionCall' in part:
                call = part['functionCall']
                calls.append({
                    'id': call.get('id') or 'call_' + uuid.uuid4().hex[:16],
                    'type': 'function',
                    'function': {'name': call['name'], 'arguments': json.dumps(call.get('args', {}))}
                })

        message = {
            'role': 'assistant',
            'content': ''.join(p.get('text', '') for p in parts if not p.get('thought')),
            'tool_calls': calls or None,
            'reasoning_details': [{'type': NATIVE_TYPE, 'model': model, 'parts': parts}]
        }
        prompt = usage.get('promptTokenCount', 0)
        output = usage.get('candidatesTokenCount', 0) + usage.get('thoughtsTokenCount', 0)
        completion = ChatCompletion(
            id='chatcmpl-' + uuid.uuid4().hex,
            object='chat.completion',
            created=int(time.time()),
            model=model,
            choices=[{
                'index': 0,
                'message': message,
                'finish_reason': 'tool_calls' if calls else ('length' if finish == 'MAX_TOKENS' else 'stop')
            }],
            usage={
                'prompt_tokens': prompt,
                'completion_tokens': output,
                'total_tokens': usage.get('totalTokenCount', prompt + output),
                'prompt_tokens_details': {'cached_tokens': usage.get('cachedContentTokenCount', 0)},
                'completion_tokens_details': {'reasoning_tokens': usage.get('thoughtsTokenCount', 0)}
            }
        )
        if stream:
            from agent.acp_openai_bridge import completion_to_stream_chunks
            chunks = completion_to_stream_chunks(completion)
            chunks[0].choices[0].delta.reasoning_details = message['reasoning_details']
            return chunks
        return completion
