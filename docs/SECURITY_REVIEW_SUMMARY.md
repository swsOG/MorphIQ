# Security Review — Summary

**Date:** June 2026 (pre-launch)
**Scope:** MorphIQ portal and document intake services.
**Method:** White-box code review plus live testing against an isolated instance seeded with
synthetic (fake) data only. No real customer data was involved.

## Purpose

Ahead of launch, we ran a structured pre-launch security review covering authentication, access
control, input handling, secrets management, dependencies, and HTTP hardening.

## Confirmed working well

- Tenant isolation — agency users could not reach other agencies' records in testing.
- CSRF protection on state-changing requests.
- Authentication required on protected pages and APIs.
- Passwords stored with a strong, salted hash (scrypt).
- Parameterised database queries (no SQL injection found).

## Hardening before launch

The review produced a prioritised set of improvements we are implementing before public launch,
spanning authentication & access hardening, input validation, production secrets/configuration,
login-abuse protections, HTTP security headers / HTTPS, and dependency updates. We follow a
"fix Critical/High before launch, harden the rest immediately after" approach. Detailed findings
are tracked privately.

## Reporting a vulnerability

Found a security issue? Please email `<add security contact, e.g. security@morphiqtechnologies.com>`
instead of opening a public issue.
