# 📦 WP Plugin Zip

**A skill for Claude Code and Claude Desktop: Claude builds WordPress plugin and theme .zip files that install the first time, and tells you why a zip won't.**

No more *"Plugin file does not exist"* or *"The package could not be installed. No valid plugins were found"*. Claude packages the plugin with a script that checks what WordPress checks, refuses to write a broken zip, and shows you the name and version before you upload it.

[English](#why) · [Español](#-en-español)

## Why

A zip that opens fine on your computer can still fail in WordPress. The causes are invisible:

- **`\` separators.** Windows PowerShell's `Compress-Archive` can write `my-plugin\my-plugin.php`. On a Linux server WordPress creates a flat file with that name instead of a folder, and the plugin "does not exist".
- **A BOM before `<?php`.** Activation fails with *headers already sent*.
- **The main file one folder too deep**, or a header past the first 8 KB, which is all WordPress reads.
- **A GitHub "Download ZIP"**: the folder becomes `my-plugin-main`, and updates no longer match the installed plugin.
- **A zip of zips** from a marketplace download.

## What it does

- **Builds** the zip with one folder named after the slug, POSIX separators and explicit folder entries.
- **Verifies before writing**: main file with `Plugin Name:` (or `style.css` with `Theme Name:`) in its first 8 KB, no BOM, no UTF-16. Optional `php -l` on every PHP file.
- **Leaves out the junk**: `.git`, `node_modules`, `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.zip`, source maps and logs.
- **Ships LF line endings**, even from a Windows checkout.
- **Checks any existing zip** and explains each problem in plain words.
- **Shows the name, version and author** of what you are about to ship, so you don't upload an old build.

## Install

### Claude Code

As a plugin:

```text
/plugin marketplace add agenciaRSE/wp-plugin-zip
/plugin install wp-plugin-zip@wp-plugin-zip
```

Or copy `skills/wp-plugin-zip` into `~/.claude/skills/`.

Then just ask: *"package the plugin"*, *"make the release zip"* or *"why does this zip say Plugin file does not exist?"*

### Claude Desktop

Download `wp-plugin-zip.zip` from the [latest release](https://github.com/agenciaRSE/wp-plugin-zip/releases/latest) and upload it in **Settings → Capabilities → Skills**. In Claude Desktop and claude.ai chats it can check and build zips you upload to the chat; in the **Code** tab it works on your own folders.

## Use the script without Claude

```text
python wp_zip.py build <plugin-folder> [out.zip] [--lint]
python wp_zip.py check <file.zip>
```

Exit code `0` means installable, `1` means errors. Python 3, standard library only: no network, nothing installed.

Run `python skills/wp-plugin-zip/scripts/test_wp_zip.py` to check it.

## 🇪🇸 En español

**Una skill para Claude Code y Claude Desktop: Claude crea los .zip de plugins y temas de WordPress para que se instalen a la primera, y te dice por qué falla un zip.**

Se acabó el *«El archivo del plugin no existe»* y el *«No se ha podido descomprimir el paquete. No se encontraron plugins.»*.

**Por qué.** Un zip que se abre bien en tu ordenador puede fallar en WordPress:

- `Compress-Archive` de PowerShell puede escribir separadores `\`. En un servidor Linux, WordPress crea un archivo plano en lugar de la carpeta y el plugin «no existe».
- Un BOM antes de `<?php` rompe la activación con *headers already sent*.
- El archivo principal está una carpeta más abajo de lo debido.
- El «Download ZIP» de GitHub crea la carpeta `mi-plugin-main` y rompe las actualizaciones.
- Una descarga de un marketplace trae un zip dentro de otro zip.

**Qué hace.** Crea el zip con una sola carpeta con el nombre del slug y lo comprueba antes de escribirlo: la cabecera `Plugin Name:` en los primeros 8 KB, sin BOM ni UTF-16 y, si quieres, `php -l` en cada archivo PHP. Deja fuera `.git`, `node_modules` y la basura del sistema, y guarda los saltos de línea en LF. Revisa también cualquier zip que ya tengas y te muestra el nombre y la versión antes de subirlo.

**Instalación en Claude Code:** `/plugin marketplace add agenciaRSE/wp-plugin-zip` y después `/plugin install wp-plugin-zip@wp-plugin-zip`. También puedes copiar `skills/wp-plugin-zip` en `~/.claude/skills/`.

**Instalación en Claude Desktop:** descarga `wp-plugin-zip.zip` de la [última versión](https://github.com/agenciaRSE/wp-plugin-zip/releases/latest) y súbelo en **Ajustes → Capacidades → Skills**.

Hecho por [AGENCIA RSE](https://agenciarse.com). Licencia MIT.
