# Repo Séance demo rehearsal

This script uses a fresh GitHub import and the installable `ghosttrace` CLI.
Do not run the example shell commands other than typing them into GhostTrace;
they are classified as text and are never executed by the tool.

## 1. Start the local stack

Start Docker Desktop and Ollama, then from the repository root:

```powershell
docker compose -f infra/docker-compose.yml up -d
ollama pull gemma2:2b
ollama pull nomic-embed-text
```

In the root `.env`, set `GHOSTTRACE_ENABLED=true` and `CLONE_DEPTH=0`.
`CLONE_DEPTH=0` imports the full history of the default branch; a positive
value intentionally makes a shallow clone. Start the API and web preview in
separate terminals:

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

```powershell
cd apps/web
pnpm dev
```

The web terminal is the visual preview. Use the CLI below for the actual
GhostTrace command-classification demonstration.

## 2. Import a fresh real repository

From a third PowerShell window at the repository root:

```powershell
$body = '{"url":"https://github.com/SomSatwik/repo-seance"}'
$import = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/repos/ingest' `
  -Method Post -ContentType 'application/json' -Body $body
$repoId = $import.repo_id
do {
  Start-Sleep -Seconds 2
  $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/repos/$repoId/status"
} while ($status.status -eq 'pending')
$status | ConvertTo-Json -Depth 6
```

Wait for `completed`. The rehearsal's fresh import completed as repository
`10` with **18 commits** and a non-shallow clone. The model's explanations and
Q&A cite the imported repository's own indexed README and commit history.

## 3. Ask a grounded question

```powershell
$question = @{
  question = 'What happened to this project, who worked on it, and what should be done next?'
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/repos/$repoId/ask" `
  -Method Post -ContentType 'application/json' -Body $question |
  ConvertTo-Json -Depth 6
```

In the verified fresh-import run, the answer identified the project from
`[readme:README.md]` and its creator from `[commit:4c8e5ebe]`, and returned
both source references in the `citations` array. The exact commit hash will
change as the project advances; check the response's citations rather than
reading a hard-coded hash aloud.

## 4. Run GhostTrace in the actual terminal

Install once from the repository root, then use the fresh import's ID:

```powershell
pip install -e packages/ghosttrace-cli
ghosttrace --repo $repoId
```

Enter these commands one at a time; they are not executed:

```text
rm -rf ./build
rm old_note.txt
ls -la
exit
```

Verified live against the fresh import: `rm -rf ./build` returned
`DESTRUCTIVE`, `rm old_note.txt` returned `CAUTION`, and `ls -la` returned
`SAFE`. The CLI printed real indexed evidence references (for example
`commit:60186a9a`, `commit:4c8e5ebe`, and `commit:fbca8b87`) with each
explanation; commands are sent as text and are never executed.

## 5. Show the visual preview

Open <http://localhost:3000/ghosttrace> to show the browser-based horror
visual identity. The browser terminal is a preview surface, not the command
input used in this demo; GhostTrace's installable product is the CLI.

## Rehearsal notes

- The first clean import used the previous `CLONE_DEPTH=1` setting and only
  exposed the tip commit. The setting now defaults to full history
  (`CLONE_DEPTH=0`); use that for demos about repository chronology.
- The composite question worked and included citations, but Gemma's answer
  should not be presented as a complete release/status audit: retrieved
  evidence is limited to indexed history and source material.
- `/roadmap` is implemented, but was cut from the demo: its live response
  offered generic recommendations and inaccurately framed the repository as a
  GhostTrace project. Do not present that response as a reliable project
  roadmap.
- Local Gemma generation can take around 23 seconds on this machine's
  CPU-backed inference. Allow the response to finish rather than retrying.
