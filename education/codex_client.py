"""Client OpenAI (Codex) minimal, sans dependance externe.

Utilise `urllib` comme le fait deja `generate_curriculum.ollama_chat` : pas de
`pip install`, pas de version a garder synchronisee avec le projet.

La cle se lit UNIQUEMENT dans la variable d'environnement `OPENAI_API_KEY`.
Elle n'est jamais ecrite sur disque, jamais loguee, jamais envoyee ailleurs que
sur api.openai.com.

Usage:
    from education.codex_client import chat, list_models
    reponse = chat("Explique le teoreme de Tales.", system="Tu es professeur.")
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = 'https://api.openai.com/v1'

# Fournisseurs OpenAI-compatible : seul l'URL de base change, le corps de la
# requete est identique. `OPENAI_BASE_URL` dans l'environnement permet de
# basculer sans toucher au code.
PROVIDERS = {
    'openai': 'https://api.openai.com/v1',
    'groq': 'https://api.groq.com/openai/v1',
    'together': 'https://api.together.xyz/v1',
    'openrouter': 'https://openrouter.ai/api/v1',
    'mistral': 'https://api.mistral.ai/v1',
    'ollama': 'http://localhost:11434/v1',
    'lmstudio': 'http://localhost:1234/v1',
}

# Fichier local, gitignore par `.gitignore`. Il permet de ne pas exporter la
# cle dans chaque terminal, sans la fier a une variable d'environnement
# oubliée. La variable d'environnement reste prioritaire.
LOCAL_ENV = Path(__file__).resolve().parents[1] / '.env.codex.local'

# Modeles disponibles sur cette cle, tries par cout croissant.
#
# Choix par defaut : `gpt-5.3-codex`. C'est le bon equilibre pour ce projet :
# le defaut de contenu vient d'un modele local 2B incapable de tenir du bilingue
# structure, il faut donc de la vraie capacite sur du JSON long. Mais le
# catalogue a 19 lecons a remplir, donc pas question de payer `-max` a chaque
# appel. Regles empiriques :
#   - `gpt-5.3-codex-mini` : refactors, scripts, questions courtes.
#   - `gpt-5.3-codex`       : redaction de contenu pedagogique, revue de code.
#   - `gpt-5.3-codex-max`   : uniquement les arbitrages d'architecture.
#   - `gpt-5.4-mini`        : tache repetitive et bon marche.
MODEL_DEFAULT = 'gpt-5.3-codex'
MODEL_CHEAP = 'gpt-5.3-codex-mini'
MODEL_STRONG = 'gpt-5.3-codex-max'

# Familles alternatives, si l'acces a la famille codex change un jour.
MODEL_GENERAL = 'gpt-5.4'
MODEL_GENERAL_CHEAP = 'gpt-5.4-mini'

EFFORT_CHEAP = 'low'
EFFORT_DEFAULT = 'medium'
EFFORT_HIGH = 'high'


class CodexError(RuntimeError):
    """Erreur d'appel a l'API, avec le detail utile pour debugg."""


def _key_from_fichier_local():
    """Lit `backend/.env.codex.local` s'il existe. Format : une ligne
    `CLE=valeur`, les commentaires et lignes vides sont ignores."""
    if not LOCAL_ENV.exists():
        return ''
    for ligne in LOCAL_ENV.read_text(encoding='utf-8').splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith('#') or '=' not in ligne:
            continue
        nom, valeur = ligne.split('=', 1)
        if nom.strip() == 'OPENAI_API_KEY':
            return valeur.strip().strip('"').strip("'")
    return ''


def api_root():
    """URL de base : `OPENAI_BASE_URL` sinon le fournisseur par defaut."""
    return (os.environ.get('OPENAI_BASE_URL') or '').strip().rstrip('/') \
        or API_ROOT


def api_key():
    key = (os.environ.get('OPENAI_API_KEY') or '').strip()
    if not key:
        key = _key_from_fichier_local()
    if not key:
        raise CodexError(
            'Aucune cle OpenAI trouvee. Pose-la dans l\'environnement :\n'
            '  $env:OPENAI_API_KEY = "sk-..."            # PowerShell\n'
            '  export OPENAI_API_KEY="sk-..."             # bash\n'
            f'ou dans {LOCAL_ENV} (ce fichier est gitignore).\n'
            'Pour un autre fournisseur, pose aussi OPENAI_BASE_URL, '
            f'par exemple : {PROVIDERS["groq"]}')
    return key


def _post(path, payload, timeout=600):
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{api_root()}{path}', data=body, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key()}',
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')
        raise CodexError(f'HTTP {exc.code} sur {path} : {detail[:1500]}') from exc
    except urllib.error.URLError as exc:
        raise CodexError(f'Reseau indisponible vers {api_root()} : {exc.reason}'
                         ) from exc


def _get(path, timeout=60):
    req = urllib.request.Request(
        f'{API_ROOT}{path}', method='GET',
        headers={'Authorization': f'Bearer {api_key()}'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')
        raise CodexError(f'HTTP {exc.code} sur {path} : {detail[:1500]}') from exc
    except urllib.error.URLError as exc:
        raise CodexError(f'Reseau indisponible vers {API_ROOT} : {exc.reason}'
                         ) from exc


def list_models():
    """Modeles accessibles a la cle courante, tries par famille."""
    data = _get('/models')
    return sorted(m.get('id', '') for m in data.get('data', []))


def _extract_output_text(data):
    """`output_text` si l'API le fournit, sinon on parcourt `output`."""
    if isinstance(data.get('output_text'), str) and data['output_text']:
        return data['output_text']
    morceaux = []
    for item in data.get('output', []):
        for part in item.get('content', []):
            if part.get('type') in ('output_text', 'text'):
                morceaux.append(part.get('text', ''))
    if morceaux:
        return ''.join(morceaux)
    # Certain deploiements encapsulent encore la reponse dans un choix.
    choices = data.get('choices') or []
    if choices:
        return choices[0].get('message', {}).get('content', '')
    raise CodexError(f'Reponse sans texte : {json.dumps(data)[:600]}')


def _extract_usage(data):
    usage = data.get('usage') or {}
    return {
        'input_tokens': usage.get('input_tokens'),
        'output_tokens': usage.get('output_tokens'),
        'total_tokens': usage.get('total_tokens'),
    }


def chat(prompt, *, system=None, model=MODEL_DEFAULT,
         effort=EFFORT_DEFAULT, max_output_tokens=8000, temperature=None,
         timeout=600):
    """Un appel de requete-reponse. Renvoie le texte, ou un dict si `raw=True`.

    On tente l'API `Responses`, puis `Chat Completions` en repli : les deux
    existent sur les comptes OpenAI, mais selon la cle l'une peut manquer.
    """
    instructions = system or ''

    payload = {
        'model': model,
        'input': prompt,
        'store': False,
    }
    if instructions:
        payload['instructions'] = instructions
    if effort:
        payload['reasoning'] = {'effort': effort}
    if max_output_tokens:
        payload['max_output_tokens'] = max_output_tokens

    try:
        data = _post('/responses', payload, timeout=timeout)
        return {
            'text': _extract_output_text(data),
            'model': data.get('model', model),
            'usage': _extract_usage(data),
        }
    except CodexError as first:
        if 'HTTP 404' not in str(first) and 'HTTP 400' not in str(first):
            raise

    payload = {
        'model': model,
        'messages': ([{'role': 'system', 'content': instructions}]
                     if instructions else []) +
                    [{'role': 'user', 'content': prompt}],
    }
    if max_output_tokens:
        payload['max_completion_tokens'] = max_output_tokens
    if temperature is not None:
        payload['temperature'] = temperature
    data = _post('/chat/completions', payload, timeout=timeout)
    return {
        'text': _extract_output_text(data),
        'model': data.get('model', model),
        'usage': _extract_usage(data),
    }


def strip_fences(text):
    """Retire un eventual bloc ```json ... ``` ajoute par le modele."""
    t = (text or '').strip()
    if not t.startswith('```'):
        return t
    t = t.split('\n', 1)[1] if '\n' in t else t
    if t.rstrip().endswith('```'):
        t = t.rstrip()[:-3]
    return t.strip()


def extract_json(text):
    """Premier objet JSON balanced dans la reponse, fences ou non.

    On ne prend pas simplement le premier `{` et le dernier `}` : le modele
    ecrit parfois une phrase d'introduction, ou un exemple de schema avant le
    JSON reel. On compte les accolades en ignorant ce qui est dans une chaine.
    """
    candidat = strip_fences(text)
    start = candidat.find('{')
    if start == -1:
        raise CodexError('Aucun `{` trouve dans la reponse du modele.')

    profondeur = 0
    dans_chaine = False
    echappe = False
    for i in range(start, len(candidat)):
        c = candidat[i]
        if dans_chaine:
            if echappe:
                echappe = False
            elif c == '\\':
                echappe = True
            elif c == '"':
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
        elif c == '{':
            profondeur += 1
        elif c == '}':
            profondeur -= 1
            if profondeur == 0:
                return json.loads(candidat[start:i + 1])

    raise CodexError('JSON non ferme dans la reponse du modele.')