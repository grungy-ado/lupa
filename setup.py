
import subprocess
import sys
import os
from distutils.core import setup, Extension

VERSION = '0.19'

extra_setup_args = {}

# check if Cython is installed, and use it if available
try:
    from Cython.Distutils import build_ext
    import Cython.Compiler.Version
    print("building with Cython " + Cython.Compiler.Version.version)
    extra_setup_args['cmdclass'] = {'build_ext': build_ext}
    source_extension = ".pyx"
except ImportError:
    print("building without Cython")
    source_extension = ".c"

# support 'test' target if setuptools/distribute is available

if 'setuptools' in sys.modules:
    extra_setup_args['test_suite'] = 'lupa.tests.suite'
    extra_setup_args["zip_safe"] = False

# check if LuaJIT is in a subdirectory and build statically against it
def cmd_output(command):
    """
    Returns the exit code and output of the program, as a triplet of the form
    (exit_code, stdout, stderr).
    """
    proc = subprocess.Popen(command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    exit_code = proc.wait()
    if exit_code != 0:
        raise RuntimeError(stderr)
    return stdout

def check_luajit2_installed():
    try:
        cmd_output('pkg-config luajit --exists')
    except RuntimeError, e:
        # pkg-config gives no stdout when it is given --exists and it cannot
        # find the package, so we'll give it some better output
        if not e.args[0]:
            raise RuntimeError("pkg-config cannot find an installed luajit")
        raise

    version_out = cmd_output('pkg-config luajit --modversion')
    if version_out[0] != '2':
        raise RuntimeError("Expected version 2+ of luajit, but found %s" %
            version_out)

def lua_include():
    cflag_out = cmd_output('pkg-config luajit --cflags-only-I')

    def trim_i(s):
        if s.startswith('-I'):
            return s[2:]
        return s
    return map(trim_i, filter(None, cflag_out.split()))

def lua_libs():
    libs_out = cmd_output('pkg-config luajit --libs')
    return filter(None, libs_out.split())

basedir = os.path.abspath(os.path.dirname(__file__))

def find_luajit_build():
    try:
        check_luajit2_installed()
        return dict(extra_objects=lua_libs(), include_dirs=lua_include())
    except RuntimeError, e:
        print("Error finding installed luajit-2:")
        print(e.args[0])
        print("Proceding with detection of local luajit-2")

    static_libs = []
    include_dirs = []

    os_path = os.path
    for filename in os.listdir(basedir):
        if filename.lower().startswith('luajit'):
            filepath = os_path.join(basedir, filename, 'src')
            if os_path.isdir(filepath):
                libfile = os_path.join(filepath, 'libluajit.a')
                if os_path.isfile(libfile):
                    static_libs = [libfile]
                    include_dirs = [filepath]
                    print("found LuaJIT build in %s" % filepath)
                    print("building statically")
    return dict(extra_objects=static_libs, include_dirs=include_dirs)

def has_option(name):
    if name in sys.argv[1:]:
        sys.argv.remove(name)
        return True
    return False

ext_args = find_luajit_build()
if has_option('--without-assert'):
    ext_args['define_macros'] = [('PYREX_WITHOUT_ASSERTIONS', None)]

ext_modules = [
    Extension(
        'lupa._lupa',
        sources = ['lupa/_lupa'+source_extension] + (
            source_extension == '.pyx' and ['lupa/lock.pxi'] or []),
        **ext_args
        )
    ]

def read_file(filename):
    f = open(os.path.join(basedir, filename))
    try:
        return f.read()
    finally:
        f.close()

def write_file(filename, content):
    f = open(os.path.join(basedir, filename), 'w')
    try:
        f.write(content)
    finally:
        f.close()

long_description = '\n\n'.join([
    read_file(text_file)
    for text_file in ['README.rst', 'INSTALL.txt', 'CHANGES.txt']])

write_file(os.path.join('lupa', 'version.py'), "__version__ = '%s'\n" % VERSION)

if sys.version_info >= (2,6):
    extra_setup_args['license'] = 'MIT style'

# call distutils

setup(
    name = "lupa",
    version = VERSION,
    author = "Stefan Behnel",
    author_email = "stefan_ml@behnel.de",
    maintainer = "Lupa-dev mailing list",
    maintainer_email = "lupa-dev@freelists.org",
    url = "http://pypi.python.org/pypi/lupa",
    download_url = "http://pypi.python.org/packages/source/l/lupa/lupa-%s.tar.gz" % VERSION,

    description="Python wrapper around LuaJIT",

    long_description = long_description,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Cython',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Other Scripting Engines',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
    ],

    packages = ['lupa'],
#    package_data = {},
    ext_modules = ext_modules,
    **extra_setup_args
)
