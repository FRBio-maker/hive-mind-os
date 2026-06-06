# Contributing

Thanks for considering a contribution to `hive-mind-os`. This is a public
template, so the bar for changes is: does it make the template more useful or
correct for the widest range of adopters?

## How to propose a change

1. Open an issue describing the gap or improvement before writing code — this
   avoids duplicate effort and keeps the scope clear.
2. Fork the repo, make your changes on a branch, and open a pull request.
3. Keep changes focused. One fix or feature per PR; unrelated cleanups go in
   separate PRs.

## Running the tests

The wiki-template scripts have a small test suite. Install the dependencies
first:

```bash
pip install -r wiki-template/scripts/requirements.txt
```

Then run all tests from the repo root:

```bash
python -m pytest wiki-template/scripts/tests bootstrap -q
```

All tests must pass before you open a PR.

## Sanitisation requirement

This is a public template. **No personal paths, usernames, real email
addresses, or machine-specific values may appear in any committed file.**

Use generic placeholders instead:

| Instead of | Write |
|---|---|
| `/home/yourname/` | `~/` or `$HOME/` or `<your-home>/` |
| `C:\Users\yourname\` | `<your-home>\` or `~/` |
| `yourname@example.com` | `<your-email>` |
| `/mnt/c/Users/yourname` | `<your-home>` |
| any real username | `<your-username>` |

After editing, run the sanitisation grep to confirm nothing slipped through:

```bash
grep -rniE 'your-real-name|@yourdomain|/home/[a-z]+|/mnt/c|C:\\Users\\[A-Za-z]' \
  --exclude-dir=.git .
```

The output must be empty.

## Docs and code consistency

If you change a script's behaviour, update the relevant docs (README.md in the
same folder, config-templates/README.md, or docs/ as appropriate). If you
correct a doc, check that the code matches. Reviewer attention is scarce — a
change that requires readers to mentally reconcile doc and code is a change
that will be rejected or deferred.

## License

By contributing, you agree your changes will be published under the MIT licence
already in this repo.
