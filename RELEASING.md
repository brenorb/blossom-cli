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

The GitHub release triggers `.github/workflows/publish.yml`, which builds the
source distribution and platform wheels containing the upstream Rust binary,
then publishes them through OIDC. A new release is required for each package
version.

The same workflow supports `workflow_dispatch`. Use it from `main` when an
existing PyPI version needs additional platform wheels; `skip-existing` keeps
already uploaded files untouched.

If a published wheel needs a packaging repair, use the next PEP 440 post
release (for example, `0.5.6.post1`) while keeping `RUST_VERSION` pinned to
the upstream crate version. PyPI does not allow replacing an uploaded file.
