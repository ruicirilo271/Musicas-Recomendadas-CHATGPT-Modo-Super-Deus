# 🎵 ChatGPT Music Super Deus

Aplicação web em **Flask + OpenAI + YouTube API** que gera recomendações musicais personalizadas com base nos vídeos que o utilizador deu like no YouTube.

A aplicação permite:

* Entrar com conta Google/YouTube
* Carregar vídeos gostados do YouTube
* Enviar esses gostos para o ChatGPT/OpenAI
* Gerar uma playlist recomendada
* Pesquisar vídeos reais no YouTube
* Tocar as músicas numa interface moderna
* Avançar automaticamente para a próxima música
* Usar modo de fim real do vídeo através da YouTube IFrame API

---

## 🚀 Demonstração

Projeto publicado no Vercel:

```txt
https://musicas-recomendadas-chatgpt-modo-s.vercel.app
```

---

## 📁 Estrutura do projeto

```txt
projeto/
├── api/
│   └── index.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── requirements.txt
├── vercel.json
├── .env
└── README.md
```

---

## 🧠 Como funciona

A aplicação usa três partes principais:

### 1. YouTube OAuth

O utilizador entra com a sua conta Google/YouTube.
Depois a aplicação consegue ler os vídeos que o utilizador marcou com like.

Endpoint usado:

```txt
GET https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,status&myRating=like
```

---

### 2. OpenAI / ChatGPT

Os vídeos gostados são enviados para a OpenAI API.
O ChatGPT analisa o gosto musical e devolve uma playlist em JSON com:

* artista
* título
* motivo da recomendação
* query para procurar no YouTube
* vibe da música
* duração estimada

---

### 3. YouTube Data API + Player

A aplicação pesquisa cada música recomendada na YouTube Data API e tenta escolher vídeos que possam tocar dentro da aplicação.

Depois usa a **YouTube IFrame Player API** para tocar os vídeos e detetar quando uma música acaba.

Quando o vídeo termina, a aplicação avança automaticamente para a próxima música.

---

## ⚙️ Requisitos

* Python 3.10+
* Conta OpenAI Platform
* Projeto no Google Cloud
* YouTube Data API v3 ativa
* OAuth Client ID do tipo **Web application**
* Conta Vercel para publicar

---

## 📦 Instalação local

Clona o repositório:

```bash
git clone https://github.com/teu-utilizador/teu-repositorio.git
cd teu-repositorio
```

Instala as dependências:

```bash
pip install -r requirements.txt
```

Cria o ficheiro `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sk-proj-A_TUA_CHAVE_OPENAI
OPENAI_MODEL=gpt-4.1-mini

YOUTUBE_API_KEY=AIzaSyA_TUA_CHAVE_YOUTUBE

YOUTUBE_CLIENT_ID=O_TEU_CLIENT_ID.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-O_TEU_CLIENT_SECRET
YOUTUBE_REDIRECT_URI=http://127.0.0.1:5000/oauth2callback

SECRET_KEY=uma-chave-grande-e-fixa-super-deus
```

Corre a aplicação:

```bash
python api/index.py
```

Abre no browser:

```txt
http://127.0.0.1:5000
```

---

## 🔑 Variáveis de ambiente

| Variável                | Descrição                             |
| ----------------------- | ------------------------------------- |
| `OPENAI_API_KEY`        | Chave da OpenAI API                   |
| `OPENAI_MODEL`          | Modelo usado para gerar recomendações |
| `YOUTUBE_API_KEY`       | Chave da YouTube Data API v3          |
| `YOUTUBE_CLIENT_ID`     | Client ID do OAuth Google             |
| `YOUTUBE_CLIENT_SECRET` | Client Secret do OAuth Google         |
| `YOUTUBE_REDIRECT_URI`  | URL de callback OAuth                 |
| `SECRET_KEY`            | Chave fixa usada pela sessão Flask    |

---

## 🔐 Configuração no Google Cloud

Vai ao Google Cloud Console:

```txt
https://console.cloud.google.com/
```

Cria ou escolhe um projeto.

Depois ativa:

```txt
YouTube Data API v3
```

Vai a:

```txt
APIs & Services → Credentials
```

Cria uma credencial:

```txt
Create Credentials → OAuth client ID
```

Escolhe:

```txt
Application type: Web application
```

---

## 🌐 URLs autorizados no Google Cloud

Para correr localmente, adiciona:

### Authorized JavaScript origins

```txt
http://127.0.0.1:5000
```

### Authorized redirect URIs

```txt
http://127.0.0.1:5000/oauth2callback
```

Para publicar no Vercel, adiciona:

### Authorized JavaScript origins

```txt
https://musicas-recomendadas-chatgpt-modo-s.vercel.app
```

### Authorized redirect URIs

```txt
https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback
```

Importante:

* Em **Authorized JavaScript origins** não coloques `/oauth2callback`
* Não coloques barra final `/`
* Em **Authorized redirect URIs** tens de colocar o caminho completo `/oauth2callback`

---

## 👤 Utilizadores de teste no Google OAuth

Se a app estiver em modo **Testing**, adiciona o teu email em:

```txt
OAuth consent screen → Audience → Test users
```

Exemplo:

```txt
teu-email@gmail.com
```

Se não adicionares o email, a Google pode bloquear o acesso.

---

## ▲ Publicar no Vercel

O ficheiro `vercel.json` deve estar assim:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

No Vercel, vai a:

```txt
Project Settings → Environment Variables
```

Adiciona:

```env
OPENAI_API_KEY=sk-proj-A_TUA_CHAVE_OPENAI
OPENAI_MODEL=gpt-4.1-mini
YOUTUBE_API_KEY=AIzaSyA_TUA_CHAVE_YOUTUBE
YOUTUBE_CLIENT_ID=O_TEU_CLIENT_ID.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-O_TEU_CLIENT_SECRET
YOUTUBE_REDIRECT_URI=https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback
SECRET_KEY=uma-chave-grande-e-fixa-super-deus
```

Atenção: no Vercel, não coloques isto no valor:

```txt
YOUTUBE_REDIRECT_URI=https://...
```

O correto é:

```txt
Name: YOUTUBE_REDIRECT_URI
Value: https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback
```

Depois faz:

```txt
Redeploy
```

---

## 🧪 Testar configuração

Depois do deploy, abre:

```txt
https://musicas-recomendadas-chatgpt-modo-s.vercel.app/api/health
```

Deve aparecer algo parecido com:

```json
{
  "ok": true,
  "app": "ChatGPT Music Super Deus",
  "openai_key_ready": true,
  "youtube_api_key_ready": true,
  "youtube_oauth_ready": true,
  "youtube_logged_in": false,
  "model": "gpt-4.1-mini",
  "youtube_redirect_uri": "https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback"
}
```

Se `youtube_oauth_ready` estiver `false`, faltam:

```txt
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
```

Se `openai_key_ready` estiver `false`, falta:

```txt
OPENAI_API_KEY
```

Se `youtube_api_key_ready` estiver `false`, falta:

```txt
YOUTUBE_API_KEY
```

---

## 🎧 Como usar

1. Abre a aplicação.
2. Clica em **Entrar com YouTube**.
3. Autoriza a conta Google.
4. Clica em **Carregar likes do YouTube**.
5. Clica em **Gerar playlist pelos likes**.
6. Carrega em **Tocar seguidas**.

A aplicação vai tocar as músicas recomendadas uma a uma.

---

## ⏭️ Avanço automático

A app tem uma opção:

```txt
Usar duração estimada
```

Se estiver ligada:

* A aplicação avança pela duração estimada devolvida pelo ChatGPT.

Se estiver desligada:

* A música toca até ao fim real do vídeo.
* Quando o YouTube Player deteta que o vídeo terminou, avança para a próxima.

---

## 🛠️ Erros comuns

### Erro: `redirect_uri_mismatch`

O URL de callback no Vercel não é igual ao do Google Cloud.

Confirma que no Vercel tens:

```env
YOUTUBE_REDIRECT_URI=https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback
```

E no Google Cloud tens:

```txt
Authorized redirect URIs:
https://musicas-recomendadas-chatgpt-modo-s.vercel.app/oauth2callback
```

---

### Erro: `Estado OAuth inválido`

A sessão/cookie OAuth não foi guardada corretamente.

Confirma que tens uma `SECRET_KEY` fixa no Vercel:

```env
SECRET_KEY=uma-chave-grande-e-fixa-super-deus
```

Depois faz **Redeploy**.

---

### Erro: `Incorrect API key`

Provavelmente colocaste uma chave Google no lugar da OpenAI.

Chave Google normalmente começa por:

```txt
AIza...
```

Chave OpenAI normalmente começa por:

```txt
sk-proj-...
```

---

### Erro: `Video unavailable`

O vídeo existe no YouTube, mas não pode tocar embutido na aplicação.

A app tenta evitar isto procurando vídeos embutíveis, mas alguns podem continuar bloqueados por:

* direitos de autor
* restrição regional
* idade
* bloqueio de incorporação
* vídeo privado ou removido

Quando isto acontece, a aplicação tenta saltar para a próxima música.

---

## 📄 Dependências

`requirements.txt`:

```txt
flask
flask-cors
python-dotenv
openai
requests
```

---

## 🔒 Segurança

Nunca publiques no GitHub:

```txt
.env
OPENAI_API_KEY
YOUTUBE_API_KEY
YOUTUBE_CLIENT_SECRET
SECRET_KEY
```

Adiciona ao `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
```

---

## 👨‍💻 Autor

Projeto criado por Rui Cirilo.

Aplicação experimental para recomendações musicais com ChatGPT, YouTube Likes e YouTube Player.

---
