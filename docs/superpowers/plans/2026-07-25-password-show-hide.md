# Password Show/Hide Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a show/hide icon button beside every password field via a shared `PasswordField` component.

**Architecture:** One client component wraps `<input>` + eye/eye-off toggle button in a horizontal flex row. Visibility state is local. Replace all seven `type="password"` call sites.

**Tech Stack:** Next.js / React client components, next-intl, inline SVG (no icon library).

## Global Constraints

- Placement: button **beside** the field (not overlay inside)
- Icons: inline SVG eye / eye-off matching `ThemeToggle` stroke style
- i18n keys: `common.showPassword` / `common.hidePassword`
- No new dependencies; no auth/API changes

---

### Task 1: i18n strings

**Files:**
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Interfaces:**
- Produces: `common.showPassword`, `common.hidePassword` for `useTranslations("common")`

- [x] **Step 1:** Add top-level `"common"` object with show/hide password strings in EN and JA
- [x] **Step 2:** Verify JSON parses (`node -e "JSON.parse(...)"`)

---

### Task 2: `PasswordField` component

**Files:**
- Create: `web/components/PasswordField.tsx`

**Interfaces:**
- Consumes: `useTranslations("common")`
- Produces: default export `PasswordField` accepting `Omit<ComponentProps<"input">, "type">` — `className` on input; wrapper is flex row

- [x] **Step 1:** Create component with local `visible` state, toggle button `type="button"`, eye/eye-off icons
- [x] **Step 2:** Input `type={visible ? "text" : "password"}`; button `aria-label` / `title` from i18n

---

### Task 3: Replace all password call sites

**Files:**
- Modify: `web/app/[locale]/login/LoginForm.tsx`
- Modify: `web/components/admin/UserManager.tsx`
- Modify: `web/components/admin/SmtpSettingsPanel.tsx`
- Modify: `web/components/admin/AiSettingsPanel.tsx`

- [x] **Step 1:** Replace each `type="password"` `<input>` with `<PasswordField ...>` (drop `type` prop)
- [x] **Step 2:** Grep to confirm zero remaining `type="password"` in `web/`
- [x] **Step 3:** Rebuild web (`docker compose up -d --build web`) and smoke-check login + one admin field
