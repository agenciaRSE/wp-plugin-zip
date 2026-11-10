---
name: wp-plugin-zip
description: Builds and checks WordPress plugin and theme .zip packages so they install and activate cleanly. Use it whenever you package a WordPress plugin or theme for upload, a release or a client, and whenever the user reports "Plugin file does not exist", "The package could not be installed. No valid plugins were found", "The theme is missing the style.css stylesheet", "headers already sent" right after activating, or asks why a plugin zip will not install. Never build a WordPress zip with Compress-Archive, Explorer's "Send to compressed folder" or a GitHub "Download ZIP".
---

# WP Plugin Zip

WordPress rejects zips that look fine on your computer. The usual causes are invisible: a `\` separator written by Windows PowerShell's `Compress-Archive`, a BOM before `<?php`, the main file one folder too deep, a GitHub folder called `slug-main`, or a zip that holds other zips. `scripts/wp_zip.py` builds the package correctly and verifies it before you hand it over.

## Build a package

```bash
python "<this skill's directory>/scripts/wp_zip.py" build <plugin-folder> [out.zip] [--lint]
```

- The folder name is the slug: `my-plugin/` gives `my-plugin.zip` with a single `my-plugin/` folder inside.
- `--lint` runs `php -l` on every PHP file when PHP is on the PATH. Use it before any release.
- Use `python3` or `py` when `python` is not found.

The script skips `.git`, `node_modules`, `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.zip`, `*.map` and logs, converts CRLF to LF in text files, and writes POSIX separators with explicit folder entries. It refuses to write the zip if:

- no PHP file directly inside the folder has a `Plugin Name:` header in its first 8 KB (and there is no `style.css` with `Theme Name:`): WordPress only reads those 8 KB;
- a PHP file starts with a UTF-8 BOM or is saved as UTF-16;
- `php -l` finds a syntax error (with `--lint`).

## Check an existing zip

```bash
python "<this skill's directory>/scripts/wp_zip.py" check <file.zip>
```

Use it on any zip before uploading it: yours, a client's or a marketplace download. Explain each ERROR line to the user in plain words and give the fix. WARNING lines install, but say what will go wrong (for example, a `-main` folder becomes the slug and breaks updates).

## Before you hand the zip over

1. Run `build`, and read its summary.
2. Confirm the **Plugin Name**, **Version** and **Author** match what you just changed. A version that did not go up means the user is about to ship an old zip.
3. Give the user the path of the zip, the version and the WARNING lines, if any.

## Writing plugin code that survives packaging

- Save PHP, JS and CSS as UTF-8 **without BOM**, with LF line endings.
- Use straight ASCII quotes (`"` `'`) in PHP code. Typographic quotes (`“ ” ‘ ’`) outside strings cause a fatal error.
- Keep the main file at `slug/slug.php` and the header at the very top of it.

## Common WordPress errors and their cause

| Message | Usual cause |
|---|---|
| Plugin file does not exist. | `\` separators, or the main file one folder too deep |
| The package could not be installed. No valid plugins were found. | Zip of zips (marketplace download), or no `Plugin Name:` header |
| The theme is missing the style.css stylesheet. | Theme zip of zips, or `style.css` one folder too deep |
| Cannot modify header information - headers already sent | BOM or blank lines before `<?php` |
| Destination folder already exists. | Same slug already installed; replace it from the upload screen or delete it first |
