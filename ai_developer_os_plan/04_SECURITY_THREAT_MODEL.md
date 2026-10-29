# Security Threat Model — RepoPilot

## 1. Assets to protect
- User source code and uncommitted changes.
- Credentials, SSH keys, cloud tokens, environment variables.
- Local filesystem and processes.
- Git history and remote repository permissions.
- Model prompts, source excerpts, logs, and generated artifacts.
- User approval integrity.
- Test environment and host OS.

## 2. Trust boundaries
1. Desktop UI to local API.
2. LLM output to tool gateway.
3. Repository content to model context.
4. Tool gateway to host filesystem/Git.
5. Sandbox to host OS.
6. Local runtime to optional external model provider.
7. Generated patch to original repository.
8. User approval event to action executor.

## 3. Threats
- Prompt injection in README, comments, issues, logs, or tests.
- Malicious build/test scripts.
- Path traversal and symlink escape.
- Model-generated destructive shell commands.
- Secret leakage into embeddings, prompts, or logs.
- Local API abuse by another local process or malicious webpage.
- Stale evidence causing wrong patch.
- Approval replay or approval applied to a different diff.
- Denial of service through huge repositories or infinite loops.
- Sandbox escape or dependency supply-chain compromise.

## 4. Controls
- Treat all repository and issue content as untrusted.
- Use strict typed tools, not unrestricted shell.
- Enforce tool permissions in code.
- Bind API to loopback and require a per-session authorization token.
- Validate origin/CSRF protections where relevant for local web interfaces.
- Canonicalize paths and check symlinks after resolution.
- Use isolated worktrees and sandbox containers.
- Do not mount secrets or host credentials.
- Disable network by default in sandbox.
- Apply CPU, memory, disk, process, and time limits.
- Require approval tied to immutable diff/action hash.
- Re-check base commit and worktree state before execution.
- Redact secrets from logs and context.
- Exclude likely secrets and binary/large files from indexing.
- Use dependency lockfiles, license audit, and security scanning.
- Clean up processes and temporary data on cancellation.

## 5. Approval policy
Read-only operations can run automatically within a user-selected repository. Patch generation can run in an isolated worktree after the user asks for it. Applying a patch, remote push, PR creation, deployment, deleting files, or any operation outside the sandbox requires explicit confirmation. MVP does not support automatic deployment or merge.

## 6. Security tests
- Path traversal attempts.
- Symlink pointing outside repository.
- Malicious repository asks agent to reveal secrets.
- Test script attempts to read home directory.
- Test script attempts outbound network.
- Prompt injection in source comments.
- Replayed approval event.
- Diff changes files outside expected scope.
- Cancel during test process.
- Model returns malformed tool arguments.
- Huge output or endless tool loop.
- Local API request without session token.

## 7. Residual risks
A container is not a perfect security boundary. A local model can still produce incorrect or unsafe code. Tests may not cover all behavior. Users must review diffs and should not run untrusted repositories on sensitive machines without appropriate isolation.
