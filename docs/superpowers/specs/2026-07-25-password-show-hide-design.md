# Password Show/Hide Toggle — Design

**Date:** 2026-07-25  
**Status:** Approved

## Goal

Add a show/hide control with an icon **beside** every password field so users can reveal masked values without leaving the form.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Placement | Beside the field (separate icon button to the right of the input) |
| Architecture | Shared `PasswordField` client component (Approach A) |
| Icons | Inline SVG eye / eye-off (same stroke style as `ThemeToggle`) |
| Visibility state | Local to each `PasswordField` instance |
| i18n | New `common.showPassword` / `common.hidePassword` for `aria-label` and `title` |

## Component

**File:** `web/components/PasswordField.tsx`

- Layout: horizontal flex row — `[input flex-1] [button]` with small gap
- Button: `type="button"` so it never submits forms; toggles input `type` between `password` and `text`
- Icons: eye when value is hidden; eye-off when visible; `aria-hidden` on SVG
- Props: forward standard `<input>` props (`value`, `onChange`, `className`, `id`, `name`, `required`, `minLength`, `placeholder`, `autoComplete`, `disabled`, etc.)
- `className` applies to the **input** only; wrapper uses a fixed flex layout
- Compact call sites (e.g. UserManager reset row) keep working via existing input `className`

## Call sites (all `type="password"`)

1. `web/app/[locale]/login/LoginForm.tsx`
2. `web/components/admin/UserManager.tsx` — create user, reset password, upgrade contact→full
3. `web/components/admin/SmtpSettingsPanel.tsx`
4. `web/components/admin/AiSettingsPanel.tsx` — OpenAI + Anthropic API keys

## Out of scope

- No new icon library dependency
- No change to password validation or auth APIs
- No overlay-inside-input variant

## Success criteria

- Every password field has a working show/hide icon button beside it
- Toggle does not submit forms
- Screen readers get localized show/hide labels
- Existing field styling and autofill behavior remain intact
