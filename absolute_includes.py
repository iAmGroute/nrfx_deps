
import os
import sys
import subprocess

from collections import defaultdict

def p(*args, hold=False, **kwargs):
    if hold:
        p.held = (args, kwargs)
    else:
        if p.held:
            a, k = p.held
            p.held = None
            print(*a, **k)
        print(*args, **kwargs)

p.held = None

def makeDirs(path):
    dirs = os.path.dirname(path)
    if dirs:
        os.makedirs(dirs, exist_ok=True)

def findWithName(base_path='./', name_glob='*', drop_base=True):
    cmd  = subprocess.run(
        ['find', base_path, '-name', name_glob],
        stdout=subprocess.PIPE, check=True
    )
    skip = len(base_path) if drop_base else 0
    return [p[skip:] for p in cmd.stdout.decode('utf-8').split('\n')[:-1]]

# Remove '' and '.'
def cleanParts(parts):
    return [p for p in parts if p not in ['', '.']]

def pathToParts(path):
    parts = path.split('/')
    parts.reverse()
    name  = parts[0]
    dirs  = cleanParts(parts[1:])
    return name, dirs

def doesMatch(dirs, loc):
    return all(b in ['..', a] for a, b in zip(dirs, loc))

def findAbsolutePath(all_files, partial_path):
    name, dirs = pathToParts(partial_path)
    matches = [
        loc
        for loc in all_files[name]
        if doesMatch(dirs, loc)
    ]
    n = len(matches)
    if   n == 0:
        p('    No files found for:', partial_path)
        return False, partial_path
    elif n == 1:
        return True, '/'.join(reversed([name] + matches[0]))
    else:
        p('   ', n, 'different files found for:', partial_path)
        for match in matches:
            p('       ', '/'.join(reversed([name] + match)))
        return False, partial_path

def main(needed_dir, out_dir):
    # `needed_dir` must be in the current directory
    if not needed_dir.endswith('/'): needed_dir += '/'
    if not    out_dir.endswith('/'): out_dir    += '/'
    assert './' not in needed_dir
    # All files in current directory
    all_files = defaultdict(list)
    for name_glob in ['*.h', '*.c']:
        paths = findWithName('./', name_glob)
        for path in paths:
            name, dirs = pathToParts(path)
            all_files[name].append(dirs)
    # All files in `needed_dir`,
    # which we will modify and copy to the `out_dir`
    filepaths = set()
    for name_glob in ['*.h', '*.c']:
        filepaths.update(findWithName(needed_dir, name_glob, False))
    # Go through the above and their dependencies,
    # replace the '#include' statements with paths relative to './'
    # and output the resulting files to `out_dir`.
    try:
        seen = filepaths.copy()
        while filepaths:
            path = filepaths.pop()
            path_out = out_dir + path
            p('Opening', path, '->', path_out, hold=True)
            with open(path) as fi:
                makeDirs(path_out)
                with open(path_out, 'wt') as fo:
                    for line in fi:
                        if line.lstrip().startswith('#include '):
                            for delim in [('"', '"'), ('<', '>')]:
                                if delim[0] in line:
                                    break
                            else:
                                p('    Expected ["] or [<] in line: "', line[:-1], '"')
                                continue
                            a, _, rest   = line.partition(delim[0])
                            name, _, b   = rest.partition(delim[1])
                            ok, new_name = findAbsolutePath(all_files, name.strip())
                            new_line     = ''.join([a, '<', new_name, '>', b])
                            if ok and new_name not in seen:
                                seen.add(new_name)
                                filepaths.add(new_name)
                            # p(f'    {line[:-1]} -> {new_line[:-1]}')
                            line = new_line
                        fo.write(line)
        p('Done', hold=True)
    finally:
        p()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

