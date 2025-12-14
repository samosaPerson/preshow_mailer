# Release & macOS Packaging Guide

These steps build a single-file macOS executable plus a `config` folder, then publish them with a GitHub release. Run commands from the repository root.

## 1) Build the one-file macOS app
```bash
# Confirm you're using Python 3.10+ (PyInstaller works best on 3.10/3.11)
python3 --version

# Switch to the release branch
git checkout release

# Ensure dependencies are available (uses the repo's venv)
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

# Build the windowed one-file executable with bundled assets/templates/examples
pyinstaller --clean --name preshow-mailer --onefile --windowed \
  --add-data "assets:assets" \
  --add-data "src/templates:src/templates" \
  --add-data "data/examples:data/examples" \
  dashboard.py
```

## 2) Prepare the distributable folder
```bash
# Place configs beside the executable (required at runtime)
mkdir -p dist/config
cp data/examples/theatre_config.yaml dist/config/
cp data/examples/show_info.json dist/config/

# (Optional) drop API keys beside the executable; DO NOT publish this file
cp .env dist/.env
```

## 3) Smoke-test the packaged app
```bash
# Start from Terminal once to confirm it opens the browser
./dist/preshow-mailer
```
Then double-click `dist/preshow-mailer` in Finder to verify it opens `http://127.0.0.1:8050/` automatically.

## 4) Zip the release asset
```bash
cd dist
zip -r ../preshow-mailer-macos.zip preshow-mailer config
cd ..
```

## 5) Tag and publish on GitHub
```bash
git status
git add .
git commit -m "Prepare macOS release"
git push origin release

# Create a version tag and push it
git tag -a v0.1.0 -m "macOS packaged release"
git push origin v0.1.0
```

Finalize the GitHub release in the browser:
1. Open the repo → Releases → “Draft a new release”.
2. Choose the tag `v0.1.0` (or your version), target branch `release`.
3. Title/describe the release, attach `preshow-mailer-macos.zip`, and publish.
