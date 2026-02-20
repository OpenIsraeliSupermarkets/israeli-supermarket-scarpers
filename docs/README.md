# Documentation

This directory contains the Sphinx documentation for `il-supermarket-scraper`.

## Building Documentation Locally

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

### Build HTML Documentation

From the `docs/` directory:

```bash
make html
```

The generated HTML files will be in `docs/build/html/`. Open `docs/build/html/index.html` in your browser to view the documentation.

### Rebuild API Documentation

If you add new modules or change the package structure, regenerate the API documentation:

```bash
cd docs
sphinx-apidoc -o source/api ../il_supermarket_scarper --separate --force
make html
```

## GitHub Actions Workflows

Two workflows are configured:

1. **`docs.yml`**: Builds documentation on every push/PR to validate that documentation compiles without errors.
2. **`docs-pages.yml`**: Builds and deploys documentation to GitHub Pages on pushes to `main`.

## Viewing Documentation Online

Once deployed, the documentation will be available at:
`https://<username>.github.io/<repo-name>/`

## Configuration

- **`source/conf.py`**: Main Sphinx configuration file
- **`source/index.rst`**: Main documentation index page
- **`source/api/`**: Auto-generated API documentation (do not edit manually)

## Theme

The documentation uses the `sphinx_rtd_theme` (Read the Docs theme) for a clean, professional appearance.
