# AI-Powered GitHub PR Bot

🤖 **Intelligent pull request analysis, review, and auto-approval using Claude AI**

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-AI--Powered%20GitHub%20PR%20Bot-blue.svg?colorA=24292e&colorB=0366d6&style=flat&longCache=true&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAM6wAADOsB5dZE0gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAERSURBVCiRhZG/SsMxFEZPfsVJ61jbxaF0cRQRcRJ9hlYn30IHN/+9iquDCOIsblIrOjqKgy5aKoJQj4n3EX8DY7ECnEMOeQf+c9/hGtlRsuUiEd3yAAYA4Dr4++2q7dMFNE7dmNBKY0BSk5sehqPfekNzKG0+Qi3GG734+O3zwVwpPy2s2HnP+p7Xh8+dSoGg2XrTg/HcNTDajqHoDdDqNLAqFwTjZm56UCEk6dSBRqDGYSUOu66Zg+I2fNZs/M3/f/Grl/XnyF1Gw3VKCez0PN5IUfFLqvgUN4C0qNqYs5YhPL+aVZYDE4IpUk57oSFnJm4FyCqqOE0jhY2SMyLFoo56zyo6becOS5UVDdj7Vih0zp+tcMhwRpBeLyqtIjlJBFdqyoJuAn9MSL9CCVpkTx/9qAAAAABJRU5ErkJggg==)](https://github.com/marketplace/actions/ai-powered-pr-bot)

**Transform your pull request workflow** with AI-powered automation that provides intelligent code reviews, generates comprehensive descriptions, and safely auto-approves quality changes.

## ✨ Why Use This Bot?

- 🔍 **Catch Issues Early** - AI reviews every line for bugs, security issues, and best practices
- 📝 **Auto-Generate Descriptions** - Never write PR descriptions again
- ⚡ **Speed Up Reviews** - Auto-approve safe changes, focus human review on what matters
- 🛡️ **Security First** - Built-in security analysis and safe auto-approval logic

> **License Notice:** Modified version of [PR-Agent](https://github.com/Codium-ai/pr-agent) by Codium AI, licensed under AGPL v3. [Source code available here](https://github.com/jacsamell/github-pr-bot).

## 🎯 Core Features

| Feature | Description | Benefits |
|---------|-------------|----------|
| 🤖 **Auto Review** | Comprehensive code analysis with security scanning | Catch bugs, security issues, and code quality problems |
| 📋 **Auto Description** | AI-generated PR titles, summaries, and labels | Save time, improve PR documentation |
| 💡 **Code Suggestions** | Specific improvements and best practices | Learn better coding patterns, optimize performance |
| ✅ **Auto Approval** | Safe approval of low-risk changes | Speed up workflow, focus reviews on complex changes |
| 🎯 **Smart Triggers** | Flexible activation via PR events or manual commands | Control when and how the bot runs |
| 📐 **Repository Rules** | Respects official Cursor rules files in your repository | Follows your project's coding standards automatically |

## 🚀 Quick Setup

### Basic Usage

```yaml
name: AI PR Bot
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  ai-pr-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: jacsamell/github-pr-bot@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          auto_review: true
          auto_describe: true
          enable_auto_approval: false
```

### Advanced Configuration

```yaml
name: AI PR Bot
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  ai-pr-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: jacsamell/github-pr-bot@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          auto_review: true
          auto_describe: true
          auto_improve: true
          enable_auto_approval: true
          model: 'anthropic/claude-sonnet-4-20250514'
          fallback_models: 'anthropic/claude-3-5-haiku-20241022'
          max_model_tokens: '1000000'
          require_trigger: false
          fail_on_tool_error: 'all'
```

### 🚦 Reliability & failure reporting

Each enabled tool (`describe`, `review`, `improve`) runs independently: one failing never stops the
others. What changed is that a failure is now *reported* as one.

- Every run ends with a summary line, e.g. `GitHub PR Bot summary: describe=ok, review=ok, improve=FAILED`.
- `✅ <tool> completed` is only logged when the tool actually completed.
- `fail_on_tool_error` controls the step's exit code:
  - `all` (default) — fail only when every enabled tool failed (auth, quota or network outage)
  - `any` — fail as soon as one tool fails
  - `none` — never fail the step
- Model responses that can't be parsed are retried on the same model (`parse_failure_retries`,
  default `1`) before falling through to `fallback_models`. A malformed response is usually a
  sampling artifact, unlike an auth error, and a re-roll normally succeeds.
- On a parse failure the raw model response is logged (truncated). Set `CONFIG__VERBOSITY_LEVEL: 2`
  or `CONFIG__LOG_RAW_RESPONSE_ON_PARSE_FAILURE: true` in the workflow `env:` for the full text.

Self-hosted OpenAI-compatible endpoints (vLLM, SGLang, TGI) can pass provider-specific request
fields — including guided/constrained decoding options — with
`LITELLM__EXTRA_BODY: '{"guided_decoding_backend": "xgrammar"}'`.

### 🔑 Required Setup

**1. Get Your Anthropic API Key**
- Visit [Anthropic Console](https://console.anthropic.com/)
- Create an account and generate an API key
- Make sure you have Claude API access

**2. Add Secret to GitHub**
- Go to your repository → Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `ANTHROPIC_API_KEY`
- Value: Your API key from step 1

| Secret | Description | Required |
|--------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Claude API key from Anthropic | ✅ Yes |

## 📋 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `anthropic_api_key` | Anthropic API key for Claude AI | ✅ Yes | - |
| `github_token` | GitHub token for API access | ❌ No | `${{ github.token }}` |
| `auto_review` | Enable automatic code review | ❌ No | `true` |
| `auto_describe` | Enable automatic PR description generation | ❌ No | `true` |
| `auto_improve` | Enable code improvement suggestions | ❌ No | `true` |
| `enable_auto_approval` | Enable automatic approval of safe changes | ❌ No | `false` |
| `model` | AI model to use | ❌ No | `anthropic/claude-sonnet-4-20250514` |
| `fallback_models` | Comma-separated models to try, in order, if the main model fails | ❌ No | - |
| `max_model_tokens` | Maximum tokens for AI model | ❌ No | `1000000` |
| `require_trigger` | Require ##prbot trigger in PR description | ❌ No | `false` |
| `fail_on_tool_error` | When to fail the step: `all` (only when every enabled tool failed), `any`, or `none` | ❌ No | `all` |
| `parse_failure_retries` | Times to retry the same model when its response can't be parsed | ❌ No | `1` |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `review_posted` | Whether a review was posted |
| `description_updated` | Whether PR description was updated |
| `improvements_posted` | Whether improvement suggestions were posted |
| `auto_approved` | Whether PR was automatically approved |

### Optional Configuration File

Create `.pr_bot.toml`:

```toml
[config]
model = "anthropic/claude-sonnet-4-20250514"
enable_auto_approval = true
max_model_tokens = 1000000
use_cursor_rules = true  # Enable Cursor rules (default: true)

[github_action_config]
require_aidesc_trigger = true  # Requires ##prbot in PR description
auto_describe = true
auto_review = true
auto_improve = true
```

## 📐 Cursor Rules Support

The bot automatically detects and respects official Cursor rules in your repository, ensuring AI reviews follow your project's specific coding standards.

### Supported Rules Files

The bot looks for these official Cursor rules files:

**Current Format (Recommended):**
- `.cursor/rules/*.mdc` - Modern Cursor project rules files

**Legacy Format (Deprecated but supported):**
- `.cursorrules` - Legacy Cursor rules file

### Example Rules File

Create `.cursor/rules/style.mdc` in your repository:

```markdown
---
description: Code style and formatting rules
alwaysApply: true
---

# Project Coding Rules

## Code Style
- Use 2 spaces for indentation
- Prefer const over let when possible
- Always use semicolons
- Use single quotes for strings

## Naming Conventions
- Use camelCase for variables and functions
- Use PascalCase for classes and components
- Use UPPER_SNAKE_CASE for constants

## Patterns to Avoid
- Don't use console.log in production code
- Avoid nested ternary operators
- Never commit commented-out code

## Preferred Patterns
- Use TypeScript strict mode
- Prefer async/await over promises.then()
- Use destructuring for object properties
```

The bot will automatically include these rules in its analysis, ensuring consistent code reviews that match your project's standards.

By default, up to 10% of the model context (capped at 100k tokens) is allocated to Cursor rules. On 1M-context models, this allows up to 100k tokens of rules to be included.

## Usage

### Automatic Mode
- Runs on all PRs (default)
- Or add `##prbot` to PR description if `require_aidesc_trigger = true`

### Manual Commands
- `/review` - Get code review
- `/describe` - Generate PR description  
- `/improve` - Get code suggestions

## 🔒 Auto-Approval Safety

The bot uses intelligent criteria to safely auto-approve low-risk changes:

### ✅ **Safe to Auto-Approve**
- Documentation updates and README changes
- Test additions and improvements  
- Minor refactoring and code cleanup
- Configuration file updates
- Dependency updates (non-breaking)

### ❌ **Requires Human Review**
- Critical business logic changes
- Security-related code modifications
- Database schema changes
- API contract modifications
- Complex algorithmic changes

**Safety First**: The bot errs on the side of caution - when in doubt, it requests human review.

## 🔒 Security & Privacy

- **API Keys**: Your Anthropic API key is securely handled through GitHub Secrets
- **Code Privacy**: Code is only sent to Anthropic's Claude API for analysis
- **No Storage**: No code or data is permanently stored by this action
- **Permissions**: Only requires standard GitHub token permissions for PR operations

## 🤝 Contributing

Contributions are welcome! This project is based on [PR-Agent](https://github.com/Codium-ai/pr-agent) and maintains AGPL v3 licensing.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under AGPL v3 - see the [LICENSE](LICENSE) file for details.

Based on [PR-Agent](https://github.com/Codium-ai/pr-agent) by Codium AI.

## 🆘 Support

- 📖 [Documentation](https://github.com/jacsamell/github-pr-bot)
- 🐛 [Report Issues](https://github.com/jacsamell/github-pr-bot/issues)
- 💬 [Discussions](https://github.com/jacsamell/github-pr-bot/discussions)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC__KEY="your-api-key"
export GITHUB_TOKEN="your-github-token"

# Run on a specific PR
python -m pr_agent.cli --pr_url=https://github.com/owner/repo/pull/123 review
```


