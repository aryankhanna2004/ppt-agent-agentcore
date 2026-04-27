# ppt-agent-agentcore

> ### ⚠️ Preview software — expect breaking changes
>
> This repo depends on **Amazon Bedrock AgentCore Harness**, which is a
> **public preview** feature, and on the matching preview build of the
> **AgentCore CLI**. Both are under active development and have already
> shipped schema-breaking changes during this project's lifetime (see e.g.
> [aws/agentcore-cli#929](https://github.com/aws/agentcore-cli/pull/929) and
> [#931](https://github.com/aws/agentcore-cli/issues/931)).
>
> **Pinned versions this repo was built and tested against:**
>
> | Component | Version |
> | --- | --- |
> | `@aws/agentcore` (CLI) | `1.0.0-preview.2` |
> | `@aws/agentcore-cdk` | `0.1.0-alpha.22` |
> | AWS CDK | `^2.x` (as pinned in `agentcore/cdk/package.json`) |
> | Claude model | `us.anthropic.claude-opus-4-7` (geo inference, `us`) |
> | Region tested | `us-east-1` |
>
> If you're reading this later and things don't deploy, first pin to the
> versions above (`npm install -g @aws/agentcore@1.0.0-preview.2`) and
> regenerate `agentcore/cdk/` from a newer `agentcore create` if the schema
> has drifted. The underlying **`harness.json` fields (`dockerfile`,
> `sessionStoragePath`, `authorizerType`, `skills`, tool types) and the
> harness runtime behaviour itself may change without notice** while
> AgentCore Harness is still in preview.

An Amazon Bedrock **AgentCore Harness** that turns ideas, artifacts, or live
websites into polished PowerPoint decks (`.pptx`) and iterates on them on
request.

It ships a custom ARM64 container (Python + Node + LibreOffice +
`python-pptx` + `pptxgenjs` + `markitdown`), runs Anthropic's official
[PPTX skill](https://github.com/anthropics/skills/tree/main/skills), and is
wired up with:

- **Model:** Claude Opus 4.7 via Bedrock (1M-token context, 128K max output, new
  tokenizer, adaptive-thinking-capable). The system prompt has been migrated
  to 4.7's literal style per Anthropic's
  [migration guide](https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4)
  — direct `MUST` / `NEVER` rules, no "think step by step" scaffolding,
  explicit tool-use mandates.
- **Tools:** AgentCore `browser` (to scrape / screenshot live sites) and
  `code-interpreter` (sandboxed Python/Node)
- **Memory:** semantic + user-preference + summarization + episodic
- **Persistent storage:** `/mnt/data/decks/` (versioned `deck-<slug>-vN.pptx`)
- **Auth:** `AWS_IAM` (SigV4)

> Built for personal use and as an internal tool — intended to be integrated
> into larger systems rather than run as a hosted product.

---

## Why

Most people don't know how to get an LLM to produce a decent `.pptx`. Anthropic
released official skills that guide a model through real PPTX authoring
(python-pptx, pptxgenjs, layout rules, accessibility), and AWS
[announced](https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/)
that AgentCore Harnesses now support skills + a browser tool. This repo is the
thinnest possible thing that combines those pieces into something a non-expert
can actually invoke.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AgentCore Runtime (us-east-1)                              │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Harness microVM (custom Docker, ARM64)              │  │
│   │  - python-pptx / pptxgenjs / markitdown              │  │
│   │  - LibreOffice + poppler-utils                       │  │
│   │  - /opt/skills/pptx/  (Anthropic PPTX skill)         │  │
│   │  - /mnt/data/decks/   (persistent session storage)   │  │
│   └──────────────────────────────────────────────────────┘  │
│          │                │                 │               │
│   ┌──────▼─────┐   ┌──────▼──────┐   ┌──────▼──────┐        │
│   │  Bedrock   │   │  Browser    │   │  Code       │        │
│   │  Opus 4.7  │   │  tool       │   │  Interp.    │        │
│   └────────────┘   └─────────────┘   └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
        ▲
        │ SigV4 (AWS_IAM)
        │
   agentcore invoke …  ← you
```

The container image is built by **AWS CodeBuild** (via
`@aws/agentcore-cdk`'s `ContainerImageBuilder`) and pushed to ECR. No local
Docker daemon required. Everything is provisioned via CDK by the AgentCore
CLI.

---

## Repo layout

```
.
├── LICENSE
├── README.md
├── AGENTS.md                        # context for AI coding assistants
├── agentcore/
│   ├── agentcore.json               # project spec (harness + memory)
│   ├── aws-targets.example.json     # copy → aws-targets.json, set account
│   ├── .llm-context/                # TS types for the JSON configs
│   └── cdk/                         # CDK app emitted by agentcore-cli
└── app/
    └── pptagent/
        ├── harness.json             # harness spec (model, tools, skills, …)
        ├── Dockerfile               # ARM64 Python 3.12 + Node 20 + LO
        ├── system-prompt.md         # agent operating instructions
        └── skills/pptx/             # Anthropic PPTX skill (SKILL.md + refs)
```

---

## Prerequisites

- Node.js 20.x+
- Python 3.10+ (for Bedrock CLI tooling, not for the agent itself)
- AWS credentials with permission to deploy CDK, CodeBuild, IAM roles,
  Bedrock AgentCore, ECR, S3. `aws configure` or env vars.
- Access to **Claude Opus 4.7 in Bedrock** in your chosen region (request it
  once under *Bedrock → Model access*; the harness uses the geo-inference ID
  `us.anthropic.claude-opus-4-7`).
- The AgentCore CLI, pinned to the exact version this repo was built against:

  ```bash
  npm install -g @aws/agentcore@1.0.0-preview.2
  ```

  Version **`1.0.0-preview.2`** is required — earlier versions silently ignore
  the custom `dockerfile` field
  ([aws/agentcore-cli#929](https://github.com/aws/agentcore-cli/pull/929)) and
  an earlier service-side bug prevented any custom harness container from
  booting
  ([aws/agentcore-cli#931](https://github.com/aws/agentcore-cli/issues/931)).
  Newer preview releases *should* work but the Harness schema has not
  stabilised — if something breaks, pin to `1.0.0-preview.2` first.

---

## Deploy

```bash
git clone https://github.com/aryankhanna2004/ppt-agent-agentcore.git
cd ppt-agent-agentcore

# 1. Point at your AWS account + region
cp agentcore/aws-targets.example.json agentcore/aws-targets.json
# edit agentcore/aws-targets.json and replace YOUR_AWS_ACCOUNT_ID

# 2. Install CDK deps
cd agentcore/cdk && npm install && cd ../..

# 3. Deploy (CodeBuild builds the custom image, CDK provisions everything)
agentcore deploy --yes
```

First deploy takes ~8–12 minutes (CDK bootstrap + ECR + CodeBuild run + harness
creation). Subsequent deploys are much faster.

To tear down:

```bash
agentcore destroy --yes
```

---

## Interacting with the agent (AgentCore CLI)

Once deployed, the harness is available at
`arn:aws:bedrock-agentcore:<region>:<account>:runtime/harness_<project>_pptagent-...`.

```bash
# One-shot prompt
agentcore invoke pptagent \
  --prompt "Make a 5-slide deck introducing my team's project. Topic: \
serverless image moderation on AWS."

# Feed a long prompt from a file
agentcore invoke pptagent --prompt "$(cat my-prompt.txt)"

# Open a shell inside the running harness microVM (handy for debugging)
agentcore invoke pptagent --exec "ls -la /mnt/data/decks/"

# Stream logs from the last run
agentcore logs pptagent --follow

# View traces (OTEL) in the AgentCore console
agentcore traces pptagent
```

### Iteration

The agent follows a strict versioning protocol defined in
[`app/pptagent/system-prompt.md`](app/pptagent/system-prompt.md):

- Every new deck is written to `/mnt/data/decks/deck-<slug>-v1.pptx`.
- Every edit creates `v2`, `v3`, … — previous versions are never overwritten.
- Within a `runtimeSessionId`, the `/mnt/data/` mount survives turns, so you
  can keep iterating ("make slide 4 punchier", "swap the theme to dark mode").

### Session persistence (`/mnt/data`) — important

The harness is deployed with managed session storage
(`filesystemConfigurations.sessionStorage.mountPath = /mnt/data`) which gives
you S3-backed persistence *scoped to a `runtimeSessionId`*. This means:

- **Same `--session-id` across invocations** → same `/mnt/data` contents
  (prior decks + user-uploaded templates are all there).
- **No `--session-id` (or a new one)** → fresh, empty `/mnt/data` → the agent
  has no memory of previous decks on disk.

To iterate across commands, reuse one session id:

```bash
SID=$(uuidgen)                                 # or any string ≥ 33 chars
agentcore invoke --harness pptagent --session-id "$SID" \
  --prompt "Build deck-onboarding-v1.pptx from <outline>…"
agentcore invoke --harness pptagent --session-id "$SID" \
  --prompt "Make slide 4 punchier and save as v2."
```

Memory (semantic / summarization / episodic) still carries across sessions;
`/mnt/data` contents do not.

### Retrieving the generated `.pptx`

The harness microVM has no direct egress to your laptop. The cleanest path is:

1. Create an S3 bucket in the same account.
2. Grant the harness execution role `s3:PutObject` / `s3:GetObject` on it.
3. Ask the agent to upload: *"Upload the latest deck to
   `s3://my-bucket/decks/`."*
4. `aws s3 cp s3://my-bucket/decks/deck-foo-v3.pptx ./`

(Large files tend to exceed the `--exec` buffer — S3 is much more reliable.)

---

## Feeding it a live URL

The built-in `browser` tool is an AgentCore-managed headless Chromium. You can
point the agent at any public (or login-gated) web app and ask it to capture
the flow:

```text
Visit https://example.com, log in with <user> / <pass>, walk through the main
screens, screenshot each, and build deck-example-intro-v1.pptx with one
screenshot per slide plus speaker notes that cite the URL.
```

Screenshots are saved under `/mnt/data/decks/<slug>-assets/` and embedded in
the deck.

---

## Future scope

**Bring-your-own PPTX template.** Today the agent uses a neutral baked-in
style (white + maroon + gold, Arial). A natural next step is to let users drop
a `template.pptx` into `/opt/templates/` (or upload it into `/mnt/data/`)
— e.g. the official AWS slide deck — and have the agent build new decks by
copying slide masters / layouts / theme colors from that template via
`python-pptx`. The `SKILL.md` already covers how to do this; it just needs a
thin UX wrapper so users can say *"use the AWS template"* and the agent picks
the file up automatically.

Other directions:

- **PDF / DOCX output** via the already-installed LibreOffice + markitdown.
- **Diagrams** via `diagrams`-py or `mermaid-cli` baked into the container.
- **Gateway integration** so other AgentCore agents can call this as a tool
  (`makeDeck(topic, sources) -> s3://…`).
- **Evaluators** for automated deck QA (no lorem ipsum, contrast ratios,
  per-slide word budget, etc.).
- **Custom browser recipes** per site (e.g. "scrape this dashboard the same
  way every week") stored in episodic memory.

---

## Troubleshooting

- **`Command '['/usr/local/bin/ctr', …, 'sleep infinity']' returned non-zero
  exit status 1`** on invoke → your CLI / service combo is older than the
  preview-2 fix. Upgrade: `npm install -g @aws/agentcore@preview` and redeploy.
  See [aws/agentcore-cli#931](https://github.com/aws/agentcore-cli/issues/931).
- **`no container URI was found in CDK outputs`** on deploy → your project's
  CDK assets were generated by an older `agentcore create`. Delete
  `agentcore/cdk/` and regenerate with the current CLI, or cherry-pick
  `ContainerImageBuilder` usage from this repo's `agentcore/cdk/lib/cdk-stack.ts`.
- **`AccessDeniedException: … bedrock:InvokeModel`** → request model access
  for Claude Opus 4.7 (`anthropic.claude-opus-4-7`, enable the geo inference
  profile `us.anthropic.claude-opus-4-7`) in the Bedrock console for the
  region in `aws-targets.json`.

---

## License

[MIT](./LICENSE). Built for internal / personal use and intended to be
integrated into other systems — contributions welcome but no support
guarantees.
