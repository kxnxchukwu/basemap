# basemap build options can be modified with the setup.cfg file. See
# setup.cfg for more information.
import sys, glob, os, numpy, subprocess
major, minor1, minor2, s, tmp = sys.version_info
if major==2 and minor1<4 or major<2:
    raise SystemExit("""matplotlib and the basemap toolkit require Python 2.4 or later.""")
from numpy.distutils.core  import setup, Extension
from distutils.util import convert_path
from distutils import ccompiler, sysconfig

def dbf_macros():
    """Return the macros to define when compiling the dbflib wrapper.

    The returned list specifies one macro, HAVE_UPDATE_HEADER, which is
    '1' if the dbflib version we will be compiling with has the
    DBFUpdateHeader function and '0' otherwise.  To check whether
    DBFUpdateHeader is available, we scan shapefil.h for the string
    'DBFUpdateHeader'.
    """
    f = open(convert_path("pyshapelib/shapelib/shapefil.h"))
    contents = f.read()
    f.close()
    if contents.find("DBFUpdateHeader") >= 0:
        return [("HAVE_UPDATE_HEADER", "1")]
    else:
        return [("HAVE_UPDATE_HEADER", "0")]

def checkversion(GEOS_dir):
    """check geos C-API header file (geos_c.h)"""
    try:
        f = open(os.path.join(GEOS_dir,'include/geos_c.h'))
    except IOError:
        return None
    geos_version = None
    for line in f:
        if line.startswith('#define GEOS_VERSION'):
            geos_version = line.split()[2]
    return geos_version

# get location of geos lib from environment variable if it is set.
if os.environ.has_key('GEOS_DIR'):
    GEOS_dir = os.environ.get('GEOS_DIR')
else:
# set GEOS_dir manually here if automatic detection fails.
    GEOS_dir = None

if GEOS_dir is None:
    # if GEOS_dir not set, check a few standard locations.
    GEOS_dirs = [os.path.expanduser('~'),'/usr','/usr/local','/sw','/opt','/opt/local']
    for direc in GEOS_dirs:
        geos_version = checkversion(direc)
        print 'checking for GEOS lib in %s ....' % direc
        if geos_version < '"3.1.1"':
            continue
        else:
            print 'GEOS lib (version %s) found in %s' % (geos_version[1:-1],direc)
            GEOS_dir = direc
            break
else:
    geos_version = checkversion(GEOS_dir)

if GEOS_dir is None:
    raise SystemExit("""
Can't find geos library . Please set the
environment variable GEOS_DIR to point to the location
where geos is installed (for example, if geos_c.h
is in /usr/local/include, and libgeos_c is in /usr/local/lib,
set GEOS_DIR to /usr/local), or edit the setup.py script
manually and set the variable GEOS_dir (right after the line
that says "set GEOS_dir manually here".""")
else:
    geos_include_dirs=[os.path.join(GEOS_dir,'include'),numpy.get_include()]
    geos_library_dirs=[os.path.join(GEOS_dir,'lib'),os.path.join(GEOS_dir,'lib64')]

# proj4 and geos extensions.
deps = glob.glob('src/*.c')
deps.remove(os.path.join('src','_proj.c'))
deps.remove(os.path.join('src','_geod.c'))
deps.remove(os.path.join('src','_geoslib.c'))

packages          = ['mpl_toolkits','mpl_toolkits.basemap']
package_dirs       = {'':'lib'}
extensions = [Extension("mpl_toolkits.basemap._proj",deps+['src/_proj.c'],include_dirs = ['src'],)]
extensions.append(Extension("mpl_toolkits.basemap._geod",deps+['src/_geod.c'],include_dirs = ['src'],))
# can't install _geoslib in mpl_toolkits.basemap namespace,
# or Basemap objects won't be pickleable.
if sys.platform == 'win32': 
# don't use runtime_library_dirs on windows (workaround
# for a distutils bug - http://bugs.python.org/issue2437).
    #extensions.append(Extension("mpl_toolkits.basemap._geoslib",['src/_geoslib.c'],
    extensions.append(Extension("_geoslib",['src/_geoslib.c'],
                                library_dirs=geos_library_dirs,
                                include_dirs=geos_include_dirs,
                                libraries=['geos_c','geos']))
else:
    #extensions.append(Extension("mpl_toolkits.basemap._geoslib",['src/_geoslib.c'],
    extensions.append(Extension("_geoslib",['src/_geoslib.c'],
                                library_dirs=geos_library_dirs,
                                runtime_library_dirs=geos_library_dirs,
                                include_dirs=geos_include_dirs,
                                libraries=['geos_c','geos']))

# check setup.cfg file to see how to install auxilliary packages.
options = {}
if os.path.exists("setup.cfg"):
    import ConfigParser
    config = ConfigParser.SafeConfigParser()
    config.read("setup.cfg")
    try: options['provide_httplib2'] = config.getboolean("provide_packages", "httplib2")
    except: options['provide_httplib2'] = 'auto'
    try: options['provide_pyshapelib'] = config.getboolean("provide_packages", "pyshapelib")
    except: options['provide_pyshapelib'] = 'auto'
else:
    options['provide_httplib2'] = 'auto'
    options['provide_pyshapelib'] = 'auto'


provide_httplib2 = options['provide_httplib2']
if provide_httplib2  == 'auto':
    print 'checking to see if httplib2 installed ..'
    try:
        import httplib2
    except ImportError:
        print 'httplib2 not installed, will be installed'
        packages = packages + ['httplib2']
        package_dirs['httplib2'] = os.path.join('lib','httplib2')
    else:
        print 'httplib2 installed'
elif provide_httplib2: # force install of httplib2
    print 'forcing install of included httplib2'
    packages = packages + ['httplib2']
    package_dirs['httplib2'] = os.path.join('lib','httplib2')
else:
    print 'will not install httplib2'

provide_pyshapelib = options['provide_pyshapelib']
if provide_pyshapelib  == 'auto':
    print 'checking to see if pyshapelib installed ..'
    try:
        import shapelib
        import dbflib
    except ImportError:
        print 'shapelib/dbflib not installed, will be installed'
        packages = packages + ['shapelib','dbflib']
        package_dirs['shapelib'] = os.path.join('lib','shapelib')
        package_dirs['dbflib'] = os.path.join('lib','dbflib')
        extensions = extensions + \
                 [Extension("shapelibc",
                            ["pyshapelib/shapelib_wrap.c",
                             "pyshapelib/shapelib/shpopen.c",
                             "pyshapelib/shapelib/shptree.c"],
                            include_dirs = ["pyshapelib/shapelib"]),
                  Extension("shptree",
                            ["pyshapelib/shptreemodule.c"],
                            include_dirs = ["pyshapelib/shapelib"]),
                  Extension("dbflibc",
                            ["pyshapelib/dbflib_wrap.c",
                             "pyshapelib/shapelib/dbfopen.c"],
                            include_dirs = ["pyshapelib/shapelib"],
                            define_macros = dbf_macros()) ]
    else:
        print 'pyshapelib installed'
elif provide_pyshapelib: # force install of shapelib
    print 'forcing install of included pyshapelib'
    packages = packages + ['shapelib','dbflib']
    package_dirs['shapelib'] = os.path.join('lib','shapelib')
    package_dirs['dbflib'] = os.path.join('lib','dbflib')
    extensions = extensions + \
             [Extension("shapelibc",
                        ["pyshapelib/shapelib_wrap.c",
                         "pyshapelib/shapelib/shpopen.c",
                         "pyshapelib/shapelib/shptree.c"],
                        include_dirs = ["pyshapelib/shapelib"]),
              Extension("shptree",
                        ["pyshapelib/shptreemodule.c"],
                        include_dirs = ["pyshapelib/shapelib"]),
              Extension("dbflibc",
                        ["pyshapelib/dbflib_wrap.c",
                         "pyshapelib/shapelib/dbfopen.c"],
                        include_dirs = ["pyshapelib/shapelib"],
                        define_macros = dbf_macros()) ]
else:
    print 'will not install pyshapelib'

# Specify all the required mpl data
# create pyproj binary datum shift grid files.
pathout =\
os.path.join('lib',os.path.join('mpl_toolkits',os.path.join('basemap','data')))
if sys.argv[1] != 'sdist':
    cc = ccompiler.new_compiler()
    sysconfig.customize_compiler(cc)
    cc.set_include_dirs(['src'])
    objects = cc.compile(['nad2bin.c'])
    execname = 'nad2bin'
    cc.link_executable(objects, execname)
    llafiles = glob.glob('datumgrid/*.lla')
    cmd = os.path.join(os.getcwd(),execname)
    for f in llafiles:
        fout = os.path.basename(f.split('.lla')[0])
        fout = os.path.join(pathout,fout)
        str = '%s %s < %s' % (cmd, fout, f)
        print 'executing ',str
        subprocess.call(str,shell=True)
datafiles = glob.glob(os.path.join(pathout,'*'))
datafiles = [os.path.join('data',os.path.basename(f)) for f in datafiles]
package_data = {'mpl_toolkits.basemap':datafiles}

setup(
  name              = "basemap",
  version           = "1.0.2",
  description       = "Plot data on map projections with matplotlib",
  long_description  = """
  An add-on toolkit for matplotlib that lets you plot data
  on map projections with coastlines, lakes, rivers and political boundaries.
  See http://www.scipy.org/wikis/topical_software/Maps for an
  example of what it can do.""",
  url               = "http://matplotlib.sourceforge.net/toolkits.html",
  download_url      = "http://sourceforge.net/projects/matplotlib",
  author            = "Jeff Whitaker",
  author_email      = "jeffrey.s.whitaker@noaa.gov",
  platforms         = ["any"],
  license           = "OSI Approved",
  keywords          = ["python","plotting","plots","graphs","charts","GIS","mapping","map projections","maps"],
  classifiers       = ["Development Status :: 4 - Beta",
                       "Intended Audience :: Science/Research", 
                       "License :: OSI Approved", 
                       "Topic :: Scientific/Engineering :: Visualization",
                       "Topic :: Software Development :: Libraries :: Python Modules",
                       "Operating System :: OS Independent"],
  packages          = packages,
  package_dir       = package_dirs,
  ext_modules       = extensions,
  package_data = package_data
  )
