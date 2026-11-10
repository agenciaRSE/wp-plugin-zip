"""Self-check: python test_wp_zip.py"""
import contextlib
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_zip  # noqa: E402

HEAD = b"<?php\n/**\n * Plugin Name: Demo\n * Version: 1.2.3\n */\n"


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = wp_zip.main(['wp_zip.py', *argv])
    return code, out.getvalue()


def write(base, files):
    for rel, data in files.items():
        p = os.path.join(base, *rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as fh:
            fh.write(data)


def make_zip(path, files):
    with zipfile.ZipFile(path, 'w') as zf:
        for name, data in files.items():
            zi = zipfile.ZipInfo('x')
            zi.filename = name  # raw name: ZipInfo() would turn "\" into "/" on Windows
            zf.writestr(zi, data)


with tempfile.TemporaryDirectory() as t:
    # build: good plugin, CRLF normalised, junk skipped, POSIX names, folder entries
    write(t, {'demo/demo.php': HEAD.replace(b'\n', b'\r\n'), 'demo/inc/a.js': b'x', 'demo/.DS_Store': b'',
              'demo/node_modules/x.js': b''})
    code, out = run('build', os.path.join(t, 'demo'))
    assert code == 0, out
    assert 'version      1.2.3' in out and 'CRLF' in out, out
    with zipfile.ZipFile(os.path.join(t, 'demo.zip')) as zf:
        names = zf.namelist()
        assert names[:2] == ['demo/', 'demo/inc/'], names
        assert set(names) == {'demo/', 'demo/inc/', 'demo/demo.php', 'demo/inc/a.js'}, names
        assert b'\r\n' not in zf.read('demo/demo.php')

    # build: BOM in PHP is an error, nothing written
    write(t, {'bom/bom.php': b'\xef\xbb\xbf' + HEAD})
    code, out = run('build', os.path.join(t, 'bom'))
    assert code == 1 and 'BOM' in out and not os.path.exists(os.path.join(t, 'bom.zip')), out

    # build: theme
    write(t, {'my-theme/style.css': b'/*\nTheme Name: My Theme\nVersion: 2.0\n*/', 'my-theme/index.php': b'<?php'})
    code, out = run('build', os.path.join(t, 'my-theme'))
    assert code == 0 and 'type         theme' in out, out

    # build: header past the first 8 KB is not seen
    write(t, {'late/late.php': b'<?php\n' + b'//' + b'x' * 9000 + b'\n' + HEAD[6:]})
    assert run('build', os.path.join(t, 'late'))[0] == 1

    # check: backslash separators
    z = os.path.join(t, 'bs.zip')
    make_zip(z, {'demo\\demo.php': HEAD})
    code, out = run('check', z)
    assert code == 1 and '"\\"' in out, out

    # check: zip of zips
    make_zip(z, {'demo.zip': b'PK', 'documentation/readme.html': b'<p>'})
    code, out = run('check', z)
    assert code == 1 and 'inner plugin zip' in out, out

    # check: main file one folder too deep
    make_zip(z, {'pack/demo/demo.php': HEAD})
    code, out = run('check', z)
    assert code == 1 and 'too deep' in out and '"demo"' in out, out

    # check: GitHub "Download ZIP" folder name -> warning, still installable
    make_zip(z, {'demo-main/demo.php': HEAD})
    code, out = run('check', z)
    assert code == 0 and 'demo-main' in out and 'WARNING' in out, out

    # check: files at the top level
    make_zip(z, {'demo.php': HEAD})
    assert run('check', z)[0] == 1

    # usage
    assert run()[0] == 2

print('ok')
