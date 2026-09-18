# API Documentation

This directory contains the API documentation hosted on GitHub Pages.

## Files
- `index.html` - Swagger UI interface
- `openapi.yaml` - OpenAPI 3.0 specification (auto-copied from user-service/)

## Local Development

To view the docs locally:

```bash
# Option 1: Simple HTTP server
cd docs
python3 -m http.server 8080
# Visit http://localhost:8080

# Option 2: Using npx
npx serve docs
```

## Deployment

The docs are automatically deployed to GitHub Pages when:
- Changes are pushed to `main` branch
- Files in `user-service/openapi.yaml` or `docs/` are modified

GitHub Pages URL: `https://fridgefinder.github.io/CFM_User/`
