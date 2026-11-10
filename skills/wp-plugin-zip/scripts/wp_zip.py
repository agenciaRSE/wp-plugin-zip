#!/usr/bin/env python3
"""Build or check a WordPress plugin or theme .zip so it installs cleanly.

    python wp_zip.py build <folder> [out.zip] [--lint]
    python wp_zip.py check <file.zip>

build  packages <folder> (named after the slug) and verifies the result.
check  diagnoses an existing zip: yours, a client's or a marketplace download.
--lint runs `php -l` on every .php file when PHP is on the PATH.

Exit code 0 = installable, 1 = errors found, 2 = bad usage.
Standard library only. Nothing is sent anywhere.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

SKIP_DIRS = {'.git', '.github', '.svn', '.hg', 'node_modules', '.idea', '.vscode', '__pycache__', '.claude'}
SKIP_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.gitignore', '.gitattributes', '.editorconfig'}
SKIP_EXT = {'.zip', '.pyc', '.log', '.map'}
TEXT_EXT = {'.php', '.js', '.css', '.txt', '.html', '.htm', '.json', '.md', '.po', '.pot', '.svg', '.xml'}
PLUGIN_FIELDS = ('Plugin Name', 'Version', 'Author', 'Text Domain', 'Requires PHP')
THEME_FIELDS = ('Theme Name', 'Version', 'Author', 'Text Domain', 'Requires PHP')
HEADER_BYTES = 8192  # get_plugin_data() / get_file_data() only read the first 8 KB


def header(data, fields):
    text = data[:HEADER_BYTES].decode('utf-8', 'replace').replace('\r\n', '\n')
    out = {}
    for f in fields:
        m = re.search(r'^[ \t/*#@]*' + re.escape(f) + r':(.*)$', text, re.I | re.M)
        if m and m.group(1).strip():
            out[f] = m.group(1).strip()
    return out


def is_junk(name):
    parts = name.rstrip('/').split('/')
    base = parts[-1]
    return (any(p in SKIP_DIRS for p in parts[:-1]) or base in SKIP_DIRS or base in SKIP_FILES
            or base.startswith('._') or '__MACOSX' in parts)


def validate(entries, names):
    """entries: {archive name: bytes} for files. names: every raw entry name.
    Returns (errors, warnings, info)."""
    errors, warnings = [], []
    if any('\\' in n for n in names):
        errors.append('entry names use "\\". WordPress on Linux creates a flat file called '
                      '"slug\\slug.php" instead of a folder ("Plugin file does not exist"). '
                      'Rebuild with this script, not Compress-Archive.')
        names = [n.replace('\\', '/') for n in names]
        entries = {k.replace('\\', '/'): v for k, v in entries.items()}

    nested = [n for n in entries if n.lower().endswith('.zip')]
    top_files = [n for n in entries if '/' not in n]
    roots = sorted({n.split('/')[0] for n in names if '/' in n})

    if nested and len(entries) <= 5 + len(nested):
        errors.append('the zip contains other zips (%s). This is a download package, not the plugin: '
                      'unzip it and upload the inner plugin zip ("No valid plugins were found").'
                      % ', '.join(nested[:3]))
    if top_files:
        errors.append('files at the top level of the zip (%s). Everything must be inside one folder '
                      'named after the slug.' % ', '.join(top_files[:3]))
    if len(roots) != 1:
        errors.append('the zip must have exactly one top folder; it has %d: %s' % (len(roots), ', '.join(roots[:5])))
        return errors, warnings, None
    slug = roots[0]

    info = None
    for name in sorted(entries):
        parts = name.split('/')
        if len(parts) == 2 and parts[1].lower().endswith('.php'):
            h = header(entries[name], PLUGIN_FIELDS)
            if 'Plugin Name' in h and (info is None or parts[1] == slug + '.php'):
                info = {'kind': 'plugin', 'main': name, **h}
    css = entries.get(slug + '/style.css')
    if info is None and css is not None:
        h = header(css, THEME_FIELDS)
        if 'Theme Name' in h:
            info = {'kind': 'theme', 'main': slug + '/style.css', **h}
    if info is None:
        deeper = [n for n in entries if n.count('/') == 2 and n.lower().endswith('.php')
                  and 'Plugin Name' in header(entries[n], PLUGIN_FIELDS)]
        if deeper:
            errors.append('the main file is one folder too deep (%s). Zip the inner folder "%s" instead.'
                          % (deeper[0], deeper[0].split('/')[1]))
        else:
            errors.append('no .php directly inside "%s/" has a "Plugin Name:" header in its first 8 KB, '
                          'and there is no style.css with "Theme Name:".' % slug)

    for name, data in entries.items():
        if os.path.splitext(name)[1].lower() not in TEXT_EXT:
            continue
        if data[:3] == b'\xef\xbb\xbf':
            msg = '%s starts with a UTF-8 BOM' % name
            if name.lower().endswith('.php'):
                errors.append(msg + ': PHP prints it before <?php ("headers already sent"). Save as UTF-8 without BOM.')
            else:
                warnings.append(msg + '.')
        elif data[:2] in (b'\xff\xfe', b'\xfe\xff'):
            errors.append('%s is UTF-16. Save it as UTF-8.' % name)
        else:
            try:
                data.decode('utf-8')
            except UnicodeDecodeError:
                warnings.append('%s is not valid UTF-8.' % name)

    if re.search(r'-(main|master|trunk|develop|v?\d+(\.\d+)+)$', slug):
        warnings.append('the folder is "%s". WordPress will use it as the slug, so updates will not match '
                        'the installed plugin. Rename it to the plain slug (GitHub "Download ZIP" adds -main).' % slug)
    junk = sorted({n for n in names if is_junk(n)})
    if junk:
        warnings.append('junk files in the zip: %s' % ', '.join(junk[:5]))
    return errors, warnings, info


def lint(paths):
    php = shutil.which('php')
    if not php:
        return [], ['--lint skipped: php is not on the PATH.']
    errors = []
    for p in paths:
        r = subprocess.run([php, '-l', p], capture_output=True, text=True)
        if r.returncode:
            errors.append('php -l: %s' % (r.stdout + r.stderr).strip().splitlines()[0])
    return errors, []


def build(src, out, want_lint):
    src = os.path.abspath(src.rstrip('/\\'))
    if not os.path.isdir(src):
        return report(['not a folder: %s' % src], [], None)
    slug = os.path.basename(src)
    out = os.path.abspath(out or os.path.join(os.path.dirname(src), slug + '.zip'))

    files, entries, crlf = [], {}, 0
    for root, dirs, names in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            path = os.path.join(root, n)
            arc = slug + '/' + os.path.relpath(path, src).replace(os.sep, '/')
            if is_junk(arc) or os.path.splitext(n)[1].lower() in SKIP_EXT or os.path.abspath(path) == out:
                continue
            with open(path, 'rb') as fh:
                data = fh.read()
            if os.path.splitext(n)[1].lower() in TEXT_EXT and b'\r\n' in data:
                data = data.replace(b'\r\n', b'\n')  # Windows checkouts add CRLF; ship LF
                crlf += 1
            files.append(path)
            entries[arc] = data
    if not entries:
        return report(['the folder is empty'], [], None)

    dirs = sorted({'/'.join(a.split('/')[:i]) + '/' for a in entries for i in range(1, a.count('/') + 1)})
    errors, warnings, info = validate(entries, dirs + list(entries))
    if want_lint:
        e, w = lint([f for f in files if f.lower().endswith('.php')])
        errors += e
        warnings += w
    if errors:
        return report(errors, warnings, info)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for d in dirs:  # explicit folder entries: some unzip tools need them
            zi = zipfile.ZipInfo(d)
            zi.external_attr = (0o40755 << 16) | 0x10
            zf.writestr(zi, b'')
        for arc, data in entries.items():
            zi = zipfile.ZipInfo(arc, date_time=(2000, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, data)
    with open(out, 'wb') as fh:
        fh.write(buf.getvalue())

    e2, w2, info = check_zip(out)  # verify what was actually written
    if crlf:
        w2.append('%d text file(s) had CRLF line endings; the zip has LF.' % crlf)
    return report(e2, warnings + w2, info, out)


def check_zip(path):
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            names = [i.orig_filename for i in zf.infolist()]  # .filename hides "\" on Windows
            entries = {i.filename: zf.read(i) for i in zf.infolist() if not i.is_dir()}
    except (zipfile.BadZipFile, OSError) as exc:
        return ['cannot open zip: %s' % exc], [], None
    errors, warnings, info = validate(entries, names)
    if bad:
        errors.insert(0, 'corrupt entry: %s' % bad)
    return errors, warnings, info


def report(errors, warnings, info, out=None):
    for w in warnings:
        print('WARNING  %s' % w)
    for e in errors:
        print('ERROR    %s' % e)
    if errors:
        print('\nNot installable: fix the errors above.')
        return 1
    if out:
        print('OK       %s (%d bytes)' % (out, os.path.getsize(out)))
    else:
        print('OK       installable')
    if info:
        print('         %-12s %s' % ('type', info['kind']))
        print('         %-12s %s' % ('main file', info['main']))
        for k in ('Plugin Name', 'Theme Name', 'Version', 'Author', 'Text Domain', 'Requires PHP'):
            if info.get(k):
                print('         %-12s %s' % (k.lower(), info[k]))
    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    if len(args) >= 2 and args[0] == 'build':
        return build(args[1], args[2] if len(args) > 2 else None, '--lint' in argv)
    if len(args) == 2 and args[0] == 'check':
        return report(*check_zip(args[1]))
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
