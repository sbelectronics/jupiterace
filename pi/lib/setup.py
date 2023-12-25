import os
import sys

from setuptools import setup, Extension

from jupsuper.version import __version__

jupsuper_ext = Extension('jupsuper.jupsuper_ext',
                     sources = ['jupsuper/jupsuper_ext.c'],
                     library_dirs = ['/usr/local/lib'],
                     libraries = ['pigpio'])


# python 3.x
# wiringpi is not supported
setup_result = setup(name='jupsuper',
      version=__version__,
      description="Scott Baker's Raspberry Jupiter Supervisor Library",
      packages=['jupsuper'],
      zip_safe=False,
      ext_modules=[jupsuper_ext]
)
