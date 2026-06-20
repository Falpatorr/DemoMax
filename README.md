# Veille « droit des affaires » — agent quotidien

A headless Claude Code agent that, every morning, reads the latest *Journal
Officiel* via the Légifrance API, summarises the items relevant to French
business law, and emails you the digest. Runs free on GitHub Actions.

## How it works

```
GitHub Actions (cron)
  └─ claude -p  (headless agent, reads CLAUDE.md + agent_prompt.md)
       └─ legifrance.py  → Légifrance JORF API (official texts, open data)
       └─ writes digest.html + subject.txt
  └─ send_email.py  → Resend  → your inbox
```

The agent step and the email step are separate on purpose: even if the agent
fails, you still get an email (with a fallback message + a link to the logs).

## Setup (about 15 minutes)

### 1. Légifrance / PISTE credentials (free)
1. Create an account at https://piste.gouv.fr/registration
2. Accept the Légifrance CGU: **API → Consentement CGU API**.
3. Create an **application**, then edit it and tick the **Légifrance** API.
4. Copy the **Client ID** and **Client Secret** (OAuth identifiers).

### 2. Resend (email)
1. Create an account at https://resend.com and get an **API key**.
2. To send from your own address, verify a domain (DNS records). For a first
   test you can set `EMAIL_FROM` to `onboarding@resend.dev` — but Resend will
   then only deliver to the email address of your own Resend account.

### 3. Anthropic API key
Get one from https://console.anthropic.com — this is what authenticates the
headless Claude Code run. (Cost is small: a daily digest is well under a cent
to a few cents per run.)

### 4. Push to GitHub and add secrets
Create a repo, push these files, then go to
**Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `PISTE_CLIENT_ID` | from step 1 |
| `PISTE_CLIENT_SECRET` | from step 1 |
| `RESEND_API_KEY` | from step 2 |
| `EMAIL_TO` | your inbox |
| `EMAIL_FROM` | e.g. `Veille Juridique <veille@your-domain.fr>` |

### 5. Test it
In the repo's **Actions** tab, open the workflow and click **Run workflow**
(`workflow_dispatch`). Check the logs and your inbox. Once happy, the daily
`cron` takes over.

## Local testing

```bash
pip install -r requirements.txt
cp .env.example .env   # fill it in
set -a; . ./.env; set +a

python legifrance.py list           # see today's JO texts as JSON
claude -p "$(cat agent_prompt.md)" --allowedTools "Bash,Read,Write"
python send_email.py
```

## Tuning

- **What counts as business law** lives in `CLAUDE.md` — edit the scope there.
- **Schedule**: change the `cron` line in `.github/workflows/daily-digest.yml`
  (it's in UTC). Note GitHub may delay scheduled runs under load.
- **Sources**: this uses the official JORF only. To add commentary/context,
  you can give the agent web access — but keep official texts as the backbone
  and have it paraphrase any press source rather than reproduce it.

## If a Légifrance call errors

The OAuth token call and `/consult/lastNJo` are stable. The script parses the
`jorfCont` / `jorf` responses generically and tries several payload shapes, so
it tolerates minor schema changes. If you still get a 400/404, check the
current Swagger for the Légifrance API on PISTE and adjust the payloads in
`legifrance.py` (clearly marked in `cmd_list` / `cmd_text`).
