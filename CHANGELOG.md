# Changelog

## [2026-05-15]

### Fixed
- **Build GitHub Actions:** movido `--onefile` do comando `pyinstaller` para dentro dos `.spec` files (`onefile=True`), pois o PyInstaller não aceita flags de makespec quando um `.spec` é passado.
- **Renomeado** `ideias.md` → `BACKLOG.md` + criado `CHANGELOG.md` separado.
