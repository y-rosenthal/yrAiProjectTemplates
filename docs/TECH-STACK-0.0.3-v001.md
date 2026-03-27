---
title: "Technical Stack (v0.0.3)"
---

# yrS3 Technical Stack (v0.0.3)

Concise reference for LLM coding tools. Project: **yrS3** — web-based tutorial and testing system.

---

## Overview

| Layer | Technology |
|-------|------------|
| **Runtime** | Node.js 20+ |
| **Framework** | Next.js 16 (App Router), React 19 |
| **Language** | TypeScript 5 (strict) |
| **Styling** | Tailwind CSS 4 (`@tailwindcss/postcss`, `@import "tailwindcss"` in `src/app/globals.css`) |
| **Auth & backend** | Supabase (Auth, PostgreSQL, Storage, Realtime) |
| **Deploy** | Vercel |

---

## Repo layout

- **App:** `src/app/` — App Router routes and API handlers (`/api/*`, `/login`, `/question-sets`, `/questions`, `/author`, etc.). Path alias `@/*` → `./src/*`.
- **Lib:** `src/lib/` — auth, Supabase client/server, questions (types, parse, validate, store-fs, store-db, sync), evaluators, question-sets, logger.
- **Middleware:** `src/middleware.ts` — auth.
- **Config:** `package.json`, `tsconfig.json`, `postcss.config.mjs`, `.env.example` (copy to `.env.local`). No `next.config.*` in repo (Next defaults).
- **Supabase:** `supabase/config.toml`, `supabase/migrations/*.sql`, `supabase/seed.sql`. DB: PostgreSQL 17; RLS on `authors`, `test_sessions`, `answers`, `audit_logs`, `question_versions`, `question_sets`, etc.
- **Docs:** `docs/` — Quarto book (`_quarto.yml`); source `.qmd`/`.md`; output `docs/_book/`.

---

## Key dependencies

- **Next.js** 16.1.6, **React** 19.2.3, **React DOM** 19.2.3
- **@supabase/ssr** ^0.8, **@supabase/supabase-js** ^2.97
- **tailwindcss** ^4, **@tailwindcss/postcss** ^4
- **js-yaml** ^4.1, **react-markdown** ^10.1, **uuid** ^13
- **TypeScript** ^5, **eslint** ^9, **eslint-config-next** 16.1.6

---

## Data & storage

- **Auth:** Supabase Auth (email/password + optional GitHub OAuth). Session via `@supabase/ssr`.
- **Database:** Supabase Postgres. Source of truth for question listing/ownership/status. Tables: `authors`, `test_sessions`, `answers`, `audit_logs`, `question_versions`, `question_sets`, `question_set_items`.
- **Question content:** Local dev — filesystem (`QUESTIONS_ROOT`, default `./questions`). Production (e.g. Vercel) — `QUESTIONS_STORAGE=supabase` and Supabase Storage bucket (`QUESTIONS_BUCKET`). Optional FS backup mirror via `QUESTIONS_FS_BACKUP_ROOT`. Sync/dual-write and `db_meta.yaml` per version; see SPEC-DB-FS-QUESTION-SYNC.
- **Question sets:** DB + optional file-based sets (`QUESTION_SETS_ROOT`, `set.yaml` per folder).

---

## Env (high level)

- **Required:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Storage:** `QUESTIONS_STORAGE` (omit/FS | `supabase`), `QUESTIONS_ROOT`, `QUESTIONS_BUCKET`, `QUESTION_SETS_ROOT`, `QUESTION_SYNC_OWNER_ID`, `QUESTIONS_FS_BACKUP_ROOT`, `NEXT_PUBLIC_APP_URL`
- **OAuth (local Supabase):** `GITHUB_CLIENT_ID`, `GITHUB_SECRET`

---

## Commands

- `npm run dev` — dev server
- `npm run build` / `npm run start` — production
- `npm run lint` — ESLint
- `supabase db reset` (or `npm run db:reset`) — reset local DB with migrations and seed

---

## Doc version

- **Doc:** TECH-STACK-0.0.3-v001 (stack snapshot for release 0.0.3).
