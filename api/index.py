# -*- coding: utf-8 -*-

import os
import json
import re
import time
import secrets
import requests

from flask import Flask, render_template, jsonify, request, session, redirect
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# -------------------------------------------------------
# Caminhos corretos para Vercel e PC
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static"),
    static_url_path="/static"
)

# -------------------------------------------------------
# Configuração de sessão para OAuth no Vercel
# -------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "troca-esta-chave-super-deus-123456789")
app.secret_key = SECRET_KEY

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

CORS(app)

# -------------------------------------------------------
# Variáveis de ambiente
# -------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "").strip()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def extract_json(text):
    if not text:
        raise ValueError("Resposta vazia da OpenAI.")

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)

    if not match:
        raise ValueError("Não foi possível encontrar JSON válido na resposta da OpenAI.")

    return json.loads(match.group(0))


def get_base_url():
    if YOUTUBE_REDIRECT_URI:
        return YOUTUBE_REDIRECT_URI.replace("/oauth2callback", "").rstrip("/")

    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)

    return f"{proto}://{host}".rstrip("/")


def get_redirect_uri():
    if YOUTUBE_REDIRECT_URI:
        return YOUTUBE_REDIRECT_URI.rstrip("/")

    return f"{get_base_url()}/oauth2callback"


def youtube_headers():
    token = session.get("youtube_access_token", "")

    if not token:
        return None

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }


def get_thumbnail(snippet):
    thumbs = snippet.get("thumbnails", {}) or {}

    if "maxres" in thumbs:
        return thumbs["maxres"].get("url", "")

    if "high" in thumbs:
        return thumbs["high"].get("url", "")

    if "medium" in thumbs:
        return thumbs["medium"].get("url", "")

    if "default" in thumbs:
        return thumbs["default"].get("url", "")

    return ""


def refresh_youtube_token_if_needed():
    refresh_token = session.get("youtube_refresh_token", "")

    if not refresh_token:
        return False

    try:
        data = {
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        r = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=15)
        token_data = r.json()

        if r.status_code != 200:
            return False

        new_access_token = token_data.get("access_token", "")

        if new_access_token:
            session["youtube_access_token"] = new_access_token
            session["youtube_token_time"] = int(time.time())
            return True

        return False

    except Exception:
        return False


def youtube_get_with_auth(url, params):
    headers = youtube_headers()

    if not headers:
        return None, {
            "ok": False,
            "login_required": True,
            "error": "Tens de iniciar sessão com o YouTube primeiro."
        }, 401

    r = requests.get(url, headers=headers, params=params, timeout=15)

    if r.status_code == 401:
        refreshed = refresh_youtube_token_if_needed()

        if refreshed:
            headers = youtube_headers()
            r = requests.get(url, headers=headers, params=params, timeout=15)

    try:
        data = r.json()
    except Exception:
        data = {}

    return r, data, r.status_code


# -------------------------------------------------------
# Página principal
# -------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------------------------------------------
# Diagnóstico
# -------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "app": "ChatGPT Music Super Deus",
        "openai_key_ready": bool(OPENAI_API_KEY),
        "youtube_api_key_ready": bool(YOUTUBE_API_KEY),
        "youtube_oauth_ready": bool(YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET),
        "youtube_redirect_uri": get_redirect_uri(),
        "youtube_logged_in": bool(session.get("youtube_access_token")),
        "model": OPENAI_MODEL
    })


# -------------------------------------------------------
# Login YouTube OAuth
# -------------------------------------------------------
@app.route("/login-youtube")
def login_youtube():
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        return jsonify({
            "ok": False,
            "error": "Faltam YOUTUBE_CLIENT_ID ou YOUTUBE_CLIENT_SECRET nas variáveis de ambiente."
        }), 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": YOUTUBE_CLIENT_ID,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": YOUTUBE_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state
    }

    auth_url = GOOGLE_AUTH_URL + "?" + requests.compat.urlencode(params)

    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    error = request.args.get("error", "")

    if error:
        return f"""
        <h1>Erro no login Google</h1>
        <p>{error}</p>
        <p><a href="/">Voltar</a></p>
        """, 400

    state = request.args.get("state", "")
    code = request.args.get("code", "")

    saved_state = session.get("oauth_state", "")

    if not state or not saved_state or state != saved_state:
        return """
        <h1>Estado OAuth inválido</h1>
        <p>Isto normalmente acontece quando a sessão/cookie não foi guardada.</p>
        <p>Confirma SECRET_KEY no Vercel e faz Redeploy.</p>
        <p><a href="/">Voltar</a></p>
        """, 400

    if not code:
        return """
        <h1>Código OAuth não recebido</h1>
        <p>O Google não devolveu o código de autorização.</p>
        <p><a href="/">Voltar</a></p>
        """, 400

    token_payload = {
        "code": code,
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code"
    }

    try:
        r = requests.post(GOOGLE_TOKEN_URL, data=token_payload, timeout=15)
        token_data = r.json()

        if r.status_code != 200:
            return f"""
            <h1>Erro ao obter token do Google</h1>
            <pre>{json.dumps(token_data, indent=2, ensure_ascii=False)}</pre>
            <p>Confirma se o Authorized redirect URI no Google Cloud é exatamente:</p>
            <pre>{get_redirect_uri()}</pre>
            <p><a href="/">Voltar</a></p>
            """, 500

        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        token_type = token_data.get("token_type", "Bearer")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            return """
            <h1>Token inválido</h1>
            <p>O Google não devolveu access_token.</p>
            <p><a href="/">Voltar</a></p>
            """, 500

        session["youtube_access_token"] = access_token
        session["youtube_token_type"] = token_type
        session["youtube_token_time"] = int(time.time())
        session["youtube_expires_in"] = expires_in

        if refresh_token:
            session["youtube_refresh_token"] = refresh_token

        session.pop("oauth_state", None)

        return redirect("/")

    except Exception as e:
        return f"""
        <h1>Erro OAuth</h1>
        <pre>{str(e)}</pre>
        <p><a href="/">Voltar</a></p>
        """, 500


@app.route("/logout-youtube")
def logout_youtube():
    session.pop("youtube_access_token", None)
    session.pop("youtube_refresh_token", None)
    session.pop("youtube_token_type", None)
    session.pop("youtube_token_time", None)
    session.pop("youtube_expires_in", None)
    session.pop("oauth_state", None)

    return redirect("/")


# -------------------------------------------------------
# Buscar vídeos com like do YouTube
# -------------------------------------------------------
@app.route("/api/youtube/liked", methods=["GET"])
def youtube_liked():
    try:
        max_results = int(request.args.get("max", 50))
    except Exception:
        max_results = 50

    max_results = max(5, min(max_results, 50))

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,contentDetails,status",
        "myRating": "like",
        "maxResults": max_results
    }

    try:
        r, data, status_code = youtube_get_with_auth(url, params)

        if r is None:
            return jsonify(data), status_code

        if status_code != 200:
            return jsonify({
                "ok": False,
                "error": data.get("error", {}).get("message", "Erro ao buscar vídeos gostados."),
                "raw": data
            }), status_code

        videos = []

        for item in data.get("items", []):
            snippet = item.get("snippet", {}) or {}
            status = item.get("status", {}) or {}
            video_id = item.get("id", "")

            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            thumbnail = get_thumbnail(snippet)

            videos.append({
                "videoId": video_id,
                "title": title,
                "channelTitle": channel,
                "thumbnail": thumbnail,
                "watchUrl": f"https://www.youtube.com/watch?v={video_id}",
                "embeddable": status.get("embeddable", None),
                "privacyStatus": status.get("privacyStatus", ""),
                "text": f"{title} - {channel}"
            })

        return jsonify({
            "ok": True,
            "count": len(videos),
            "videos": videos
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# -------------------------------------------------------
# ChatGPT recomenda músicas com base nos likes
# -------------------------------------------------------
@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    if not client:
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY não encontrada. Coloca a chave da OpenAI no Vercel."
        }), 500

    data = request.get_json(silent=True) or {}

    liked_videos = data.get("liked_videos", [])
    mood = str(data.get("mood", "")).strip()
    genres = str(data.get("genres", "")).strip()
    amount = data.get("amount", 20)

    try:
        amount = int(amount)
    except Exception:
        amount = 20

    amount = max(5, min(amount, 40))

    liked_lines = []

    for video in liked_videos[:50]:
        title = str(video.get("title", "")).strip()
        channel = str(video.get("channelTitle", "")).strip()

        if title:
            liked_lines.append(f"- {title} | Canal: {channel}")

    if not liked_lines:
        liked_lines = [
            "- Adele - Easy On Me",
            "- Rihanna - Diamonds",
            "- The Weeknd - Blinding Lights",
            "- Nininho Vaz Maia - Calon",
            "- Roberto Carlos - Detalhes",
            "- Boss AC - Sexta-feira"
        ]

    system_prompt = """
És um especialista mundial em recomendações musicais.

Tens de analisar vídeos gostados no YouTube e perceber o gosto musical do utilizador.
Deves recomendar músicas reais, populares e boas para tocar numa playlist.

Tens de devolver APENAS JSON válido.
Não uses Markdown.
Não uses texto fora do JSON.
Não inventes músicas impossíveis.
A ordem deve funcionar como uma playlist para tocar seguida.

Formato obrigatório:

{
  "playlist_name": "nome criativo da playlist",
  "description": "descrição curta baseada nos likes do YouTube",
  "taste_summary": "resumo curto do gosto musical detetado",
  "tracks": [
    {
      "artist": "Nome do artista",
      "title": "Nome da música",
      "reason": "Motivo curto ligado aos vídeos gostados",
      "youtube_query": "Nome do artista Nome da música official audio",
      "vibe": "romântica / energia / calma / kizomba / pop / R&B / etc",
      "estimated_seconds": 240
    }
  ]
}
"""

    user_prompt = f"""
Cria uma playlist com exatamente {amount} músicas recomendadas.

Estas recomendações têm de ser baseadas nos vídeos que o utilizador deu like no YouTube:

{chr(10).join(liked_lines)}

Preferências adicionais:
- Estado de espírito: {mood or "boa vibe, músicas para ouvir seguidas"}
- Géneros preferidos adicionais: {genres or "pop, kizomba, R&B, soul, música portuguesa, afro pop"}

Regras:
- Baseia as recomendações nos vídeos gostados.
- Recomenda exatamente {amount} músicas reais.
- Não repitas a mesma música.
- Não recomendes apenas os mesmos vídeos gostados; recomenda também músicas parecidas.
- Mistura músicas conhecidas com descobertas boas.
- A playlist deve começar forte e depois manter boa energia.
- A youtube_query deve preferir official audio, lyric video ou topic, porque costumam funcionar melhor em embed.
- estimated_seconds deve ser a duração aproximada da música em segundos.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        text = response.output_text.strip()
        parsed = extract_json(text)

        raw_tracks = parsed.get("tracks", [])
        cleaned_tracks = []
        used = set()

        for track in raw_tracks:
            artist = str(track.get("artist", "")).strip()
            title = str(track.get("title", "")).strip()
            reason = str(track.get("reason", "")).strip()
            vibe = str(track.get("vibe", "")).strip()

            try:
                estimated_seconds = int(track.get("estimated_seconds", 240))
            except Exception:
                estimated_seconds = 240

            estimated_seconds = max(120, min(estimated_seconds, 480))

            if not artist or not title:
                continue

            key = f"{artist.lower()}---{title.lower()}"

            if key in used:
                continue

            used.add(key)

            youtube_query = f"{artist} {title} official audio"

            cleaned_tracks.append({
                "artist": artist,
                "title": title,
                "reason": reason or "Combina com os vídeos que deste like no YouTube.",
                "youtube_query": youtube_query,
                "vibe": vibe or "boa vibe",
                "estimated_seconds": estimated_seconds
            })

        return jsonify({
            "ok": True,
            "playlist_name": parsed.get("playlist_name", "Playlist Super Deus"),
            "description": parsed.get(
                "description",
                "Músicas recomendadas pelo ChatGPT com base nos teus likes do YouTube."
            ),
            "taste_summary": parsed.get(
                "taste_summary",
                "Gosto musical analisado com base nos vídeos gostados."
            ),
            "tracks": cleaned_tracks
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# -------------------------------------------------------
# Pesquisar vídeo tocável no YouTube
# -------------------------------------------------------
@app.route("/api/youtube/search", methods=["POST"])
def youtube_search():
    if not YOUTUBE_API_KEY:
        return jsonify({
            "ok": False,
            "error": "YOUTUBE_API_KEY não encontrada. Coloca a chave do YouTube no Vercel."
        }), 500

    data = request.get_json(silent=True) or {}
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({
            "ok": False,
            "error": "Pesquisa vazia."
        }), 400

    try:
        search_url = "https://www.googleapis.com/youtube/v3/search"

        query_variants = [
            query,
            query.replace("official music video", "official audio"),
            query.replace("official video", "official audio"),
            query + " official audio",
            query + " lyric video",
            query + " topic"
        ]

        seen_queries = []
        all_video_ids = []

        for q in query_variants:
            q = " ".join(q.split())

            if not q or q.lower() in seen_queries:
                continue

            seen_queries.append(q.lower())

            search_params = {
                "key": YOUTUBE_API_KEY,
                "part": "snippet",
                "q": q,
                "type": "video",
                "videoEmbeddable": "true",
                "videoSyndicated": "true",
                "maxResults": 10,
                "safeSearch": "none",
                "order": "relevance"
            }

            search_response = requests.get(search_url, params=search_params, timeout=12)
            search_data = search_response.json()

            if search_response.status_code != 200:
                continue

            for item in search_data.get("items", []):
                video_id = item.get("id", {}).get("videoId")

                if video_id and video_id not in all_video_ids:
                    all_video_ids.append(video_id)

            if len(all_video_ids) >= 15:
                break

        if not all_video_ids:
            return jsonify({
                "ok": False,
                "error": "Nenhum vídeo encontrado no YouTube."
            }), 404

        videos_url = "https://www.googleapis.com/youtube/v3/videos"

        videos_params = {
            "key": YOUTUBE_API_KEY,
            "part": "snippet,status,contentDetails",
            "id": ",".join(all_video_ids[:50])
        }

        videos_response = requests.get(videos_url, params=videos_params, timeout=12)
        videos_data = videos_response.json()

        if videos_response.status_code != 200:
            return jsonify({
                "ok": False,
                "error": videos_data.get("error", {}).get("message", "Erro ao validar vídeos do YouTube."),
                "raw": videos_data
            }), 500

        valid_videos = []

        for item in videos_data.get("items", []):
            status = item.get("status", {}) or {}
            snippet = item.get("snippet", {}) or {}
            video_id = item.get("id", "")

            embeddable = status.get("embeddable", False)
            privacy_status = status.get("privacyStatus", "")

            if not video_id:
                continue

            if privacy_status != "public":
                continue

            if not embeddable:
                continue

            title = snippet.get("title", "").lower()
            channel = snippet.get("channelTitle", "").lower()

            score = 0

            if "official audio" in title:
                score += 10

            if "lyric" in title:
                score += 6

            if "topic" in channel:
                score += 5

            if "official" in title:
                score += 4

            if "live" in title:
                score -= 4

            if "cover" in title:
                score -= 5

            if "karaoke" in title:
                score -= 8

            if "reaction" in title:
                score -= 8

            if "remix" in title and "remix" not in query.lower():
                score -= 3

            valid_videos.append({
                "score": score,
                "item": item
            })

        if not valid_videos:
            return jsonify({
                "ok": False,
                "error": "Encontrei vídeos, mas nenhum parece poder tocar incorporado na aplicação."
            }), 404

        valid_videos.sort(key=lambda x: x["score"], reverse=True)

        best = valid_videos[0]["item"]

        video_id = best.get("id", "")
        snippet = best.get("snippet", {}) or {}

        return jsonify({
            "ok": True,
            "videoId": video_id,
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "thumbnail": get_thumbnail(snippet),
            "watchUrl": f"https://www.youtube.com/watch?v={video_id}"
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# -------------------------------------------------------
# Execução local
# -------------------------------------------------------
if __name__ == "__main__":
    print("")
    print("✨ ChatGPT Music Super Deus iniciado")
    print("🌐 Abre: http://127.0.0.1:5000")
    print("")
    app.run(host="127.0.0.1", port=5000, debug=True)