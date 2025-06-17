# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LNBits extension called "satoshimachine" (currently using template name "MyExtension"). LNBits extensions are modular add-ons that extend the functionality of the LNBits Lightning Network wallet platform.

## Development Commands

### Code Quality & Formatting
```bash
# Format all code
make format

# Check code quality
make check

# Individual commands
poetry run black .                    # Python formatting
poetry run ruff check . --fix         # Python linting with auto-fix
poetry run ./node_modules/.bin/prettier --write .  # JavaScript formatting
poetry run mypy .                     # Python type checking
poetry run ./node_modules/.bin/pyright # JavaScript type checking
```

### Testing
```bash
# Run tests
make test
# or
PYTHONUNBUFFERED=1 DEBUG=true poetry run pytest
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
make install-pre-commit-hook

# Run pre-commit on all files
make pre-commit
```

## Architecture

### Core Structure
LNBits extensions follow a specific FastAPI + Vue.js architecture:

- **Backend (Python/FastAPI)**:
  - `__init__.py` - Extension initialization and router setup
  - `models.py` - Pydantic data models
  - `crud.py` - Database operations
  - `views.py` - Frontend page routes
  - `views_api.py` - API endpoints
  - `views_lnurl.py` - LNURL protocol handlers
  - `migrations.py` - Database schema changes
  - `tasks.py` - Background tasks
  - `helpers.py` - Utility functions

- **Frontend (Vue.js 3 Options API + Quasar)**:
  - `static/js/index.js` - Main Vue app
  - `static/js/components/` - Vue components
  - `templates/` - HTML templates with Jinja2

### Key Conventions

1. **Template Syntax Rules**:
   - Use `{{ }}` and `{% %}` ONLY in `index.html` files (Jinja2)
   - In Vue components: Use `v-text='value'` instead of `{{ value }}`
   - Use `:attribute='value'` for binding, `v-html='value'` for HTML content

2. **API Patterns**:
   - Always include wallet key (inkey/adminkey) as third parameter in API calls
   - Use `LNbits.api.request()` for all API calls
   - Destructure responses: `const {data} = await LNbits.api.request(...)`

3. **Component Registration**:
   - Templates must be included BEFORE scripts in HTML
   - Components must be registered BEFORE app.mount()

### The Magical G Object
The global `this.g` object provides access to:
- `this.g.user` - Complete user data including wallets array
- `this.g.user.wallets[0].inkey` - Invoice key for API calls
- `this.g.user.wallets[0].adminkey` - Admin key for privileged operations
- `this.g.wallet` - Currently selected wallet

### Built-in Utilities
- Currency conversion: `/api/v1/currencies`, `/api/v1/conversion`
- QR code generation: `/api/v1/qrcode/{data}` or Quasar VueQrcode component
- WebSocket support: `wss://host/api/v1/ws/{id}` with POST to `/api/v1/ws/{id}/{data}`

## Configuration Files

- `config.json` - Extension configuration
- `manifest.json` - Extension manifest for installation
- `pyproject.toml` - Python dependencies and tool configuration
- `package.json` - JavaScript dependencies

## Important Notes

- This extension is currently a template with placeholder "MyExtension" naming
- The actual functionality appears to be related to "satoshimachine" based on directory structure
- The `tmp/` directory contains a more developed version with DCA (Dollar Cost Averaging) functionality
- Extensions must follow snake_case naming conventions for Python files
- Use Quasar components (QBtn, QInput, QSelect, etc.) for UI consistency
- Always implement proper loading states and error handling with `LNbits.utils.notifyApiError(error)`