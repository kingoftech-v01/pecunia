# Contributing to Pecunia

Thank you for your interest in contributing to Pecunia! We welcome contributions from everyone.

## How to Contribute

### 1. Find an Issue

- Browse [open issues](https://github.com/kingoftech-v01/pecunia/issues)
- Look for issues labeled `good first issue` for beginner-friendly tasks
- Look for issues labeled `help wanted` for tasks where we need assistance

### 2. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/pecunia.git
cd pecunia
git remote add upstream https://github.com/kingoftech-v01/pecunia.git
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 4. Set Up Your Environment

#### Backend (pecunia-web)

```bash
cd pecunia-web
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

#### Desktop (pecunia-desktop)

```bash
cd pecunia-desktop
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

#### Mobile (pecunia-mobile)

Open `pecunia-mobile` in Android Studio and sync Gradle.

### 5. Make Your Changes

- Follow the coding conventions in [MASTER_CONVENTIONS.md](./MASTER_CONVENTIONS.md)
- Write tests for new functionality
- Keep commits small and focused

### 6. Commit Your Changes

We use conventional commits:

```
feat: add budget template selection
fix: resolve token refresh race condition
docs: update API documentation
test: add transaction import tests
refactor: extract banking provider base class
```

### 7. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub targeting the `main` branch.

## Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/platform/description` | `feature/web/budget-templates` |
| Bug Fix | `fix/platform/description` | `fix/mobile/budget-deletion-crash` |
| Docs | `docs/description` | `docs/api-documentation` |
| Refactor | `refactor/platform/description` | `refactor/web/banking-providers` |

## Code Review

All submissions require review before merging. Maintainers may ask for changes. Please be patient and responsive to feedback.

## Tech Stack Quick Reference

| Platform | Language | Framework |
|----------|----------|-----------|
| Backend | Python 3.11+ | Django REST Framework |
| Desktop | Python 3.11+ | PyQt6 |
| Mobile | Kotlin | Jetpack Compose |

## Reporting Issues

- Use the issue templates provided
- Include steps to reproduce for bugs
- Include mockups or descriptions for feature requests

## Questions?

Open a [discussion](https://github.com/kingoftech-v01/pecunia/discussions) or comment on the relevant issue.

Thank you for helping make Pecunia better!
