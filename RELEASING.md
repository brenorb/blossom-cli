# Releasing

This project publishes to PyPI through GitHub Actions Trusted Publishing. No PyPI token is stored in the repository.

## One-time PyPI setup

On PyPI, add a pending trusted publisher with:

- Owner: `brenorb`
- Repository: `blossom-cli`
- Workflow: `publish.yml`
- Environment: `pypi`

The PyPI project name is `blossom-cli`. The published console script has the same name, so users can run `uvx blossom-cli ...`.

## Release

After the pending publisher is configured:

```bash
git tag v0.5.6
git push origin v0.5.6
gh release create v0.5.6 --repo brenorb/blossom-cli --generate-notes
```

The GitHub release triggers `.github/workflows/publish.yml`, which builds the package and publishes it through OIDC. A new release is required for each package version.
