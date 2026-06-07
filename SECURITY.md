# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes |

## Reporting a Vulnerability

If you discover a security vulnerability in FixerAgent, please report it responsibly.

**Do NOT open a public GitHub issue** for security bugs.

Instead, email the maintainers directly:
- **security@fixeragent.dev** (or the project owner if no dedicated address exists)

### What to Include
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)
- Your PGP public key (optional, for encrypted replies)

### Response Timeline

| Phase | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 5 business days |
| Patch or mitigation | Within 30 days (critical: 7 days) |
| Public disclosure | Coordinated with reporter |

## Scope

The following are **in scope** for vulnerability reports:
- API authentication bypass or token leakage
- Injection vulnerabilities in LLM prompt handling
- Data leakage between user sessions
- Unsafe deserialization or pickle usage
- Dependency vulnerabilities with CVSS ≥ 7.0

The following are **out of scope**:
- Social engineering of end users
- Physical device damage resulting from following repair guides (see Liability Disclaimer)
- Denial-of-service via resource exhaustion on unmanaged deployments

## Security Best Practices for Deployers

1. **Rotate API keys** for LLM providers monthly
2. **Run with least privilege** — the app does not need root
3. **Enable rate limiting** (`slowapi` / Redis) in production
4. **Sanitize user inputs** before forwarding to LLM APIs
5. **Do not log** user-uploaded images beyond session lifetime
6. **Use HTTPS only** for the public API and frontend
7. **Pin Docker base images** and rebuild weekly for security patches

## Acknowledgments

We will publicly credit reporters who responsibly disclose vulnerabilities (with their consent) in our release notes.

---

*Last updated: 2026-06-07*