---
name: Writing a Good IT Ticket
description: How to compose a well-formed ticket (summary, description, priority) when calling the it-helpdesk-function tool, plus first-line troubleshooting steps by category.
---

# Skill: Writing a Good IT Ticket

Reference for composing a well-formed ticket when calling the it-helpdesk-function
tool. The system prompt covers when and whether to raise a ticket; this skill
covers HOW to write it well.

## Summary field
One line, format: `<Category>: <short problem>`.
- `VPN: client times out with certificate error`
- `Email: Outlook not syncing (0x8004010F)`
- `Access: cannot open shared finance folder`

Categories: VPN, Wi-Fi, Password/MFA, Email, Performance, Printing, Meetings, Access, Software.

## Description field
Include these in order; write "not provided" for anything the user didn't give:
1. Symptom — what is happening
2. Exact error text — verbatim, if any
3. Device / OS and app/version
4. Scope — one user or many; location
5. Steps already tried and their result

## Priority
- **High/Urgent** — work fully blocked, many users affected, or a security / sensitive-access concern.
- **Medium** — degraded productivity with a workaround; single-user outage of a core tool.
- **Low** — minor inconvenience or a ready workaround.

## First-line steps by category (offer before raising a ticket)
- **VPN** — reopen client and retry once; check internet access; verify system clock; check status page.
- **Wi-Fi** — toggle Wi-Fi; forget/rejoin the approved network; move closer to the AP; restart.
- **Password/MFA** — use the official reset portal; confirm the correct account; never share codes.
- **Performance** — close unused apps/tabs; restart; let updates finish; check storage.
- **Email** — compare webmail vs app; check Outbox and attachment limits; restart the app.
- **Printing** — confirm the right printer/queue; clear your own stuck job; print a test page.
- **Meetings/audio** — check mute/privacy switch and selected device; grant app permissions; use headphones for echo.
- **Access/Software** — confirm correct identity and approved URL/portal; submit an access request with approval.

## Example
User: "Outlook won't sync on my Windows laptop, error 0x8004010F, started this morning."
- summary: `Email: Outlook not syncing (0x8004010F)`
- description:
  `Symptom: mailbox not updating. Error: 0x8004010F. Device/OS: Windows, Outlook desktop. Scope: single user, started this morning. Steps tried: restarted Outlook and device; webmail works.`
