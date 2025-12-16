# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

> [!NOTE]
> This project is currently pre-1.0. Security patches are provided for the latest 0.x release.

## Reporting a Vulnerability

If you discover a security vulnerability in immich-migrator, please report it responsibly:

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security issues by emailing:

**<k.github@lundgrens.net>**

Include the following information:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We'll acknowledge your report within 48 hours
- **Updates**: We'll keep you informed of progress toward a fix
- **Resolution**: We aim to release a fix within 30 days for critical issues
- **Credit**: We'll credit you in the release notes (unless you prefer anonymity)

## Security Considerations

### API Keys

immich-migrator handles sensitive Immich API keys. Please note:

- Never commit API keys to version control
- Use environment files (`.immich.env`) with appropriate permissions (`chmod 600`)
- Ensure credentials files are in `.gitignore`
- Rotate API keys if you suspect they've been compromised

### Temporary Files

The tool downloads photos to a temporary directory:

- Default location: System temp directory or specified `--temp-dir`
- Files are not encrypted at rest
- Ensure adequate disk space and permissions
- Clean up temp files after migration

### Network Security

- All communication with Immich servers uses HTTPS
- Verify SSL certificates are valid
- Be cautious when migrating over untrusted networks
- Consider using VPN for remote migrations

## Best Practices

1. **Keep Updated**: Always use the latest version
2. **Review Changes**: Check CHANGELOG.md for security-related updates
3. **Secure Environment**: Run migrations in a secure, isolated environment
4. **Access Control**: Limit API key permissions to minimum required
5. **Audit Logs**: Check Immich server logs for unexpected activity

## Disclosure Policy

When we receive a security report:

1. We'll confirm the issue and determine its severity
2. We'll develop and test a fix
3. We'll prepare a security advisory
4. We'll release a patched version
5. We'll publicly disclose the issue after users have had time to update

Thank you for helping keep immich-migrator and its users safe!
