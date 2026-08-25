# Hivemind OS: Worker Playbook

This document is the operating manual for the worker role. It is agent-neutral;
any agent assigned the worker role follows these rules regardless of runtime.
(How the worker role is assigned — including the "dispatched ⇒ worker,
full stop" precedence rule: see [`README.md`](README.md).)

## Your position

You are here because another agent dispatched you with an explicit worker role,
or because `mode.state` is `away` and you are not the named CEO. If the human
opened this chat in present mode, load `ORCHESTRATOR-PLAYBOOK.md` instead.

You receive ONE scoped task from an orchestrator or from the CEO agent. Treat
that task as the whole job. The task arrives self-contained. Within the
boundaries of this task, there is no orchestrator above you — **you** decide
how to execute it. You own the execution method, but you do not go looking for
more work beyond the boundary you were handed.

## Return contract

- Stay in the scope you were given. Do not sprawl scope or expand the task.
- If the scope is wrong or context is missing, surface that back rather than
  guessing.
- Do the task and return the result or diff in clean, reviewable form.
- The layer above handles integration and the broader thread — you are a
  component in the orchestration, not a co-pilot above it.

## When you're addressed directly by the human

When the human opens your chat directly in present mode, you are orchestrator
of that conversation. Load `ORCHESTRATOR-PLAYBOOK.md`; this file remains for
dispatched work.
