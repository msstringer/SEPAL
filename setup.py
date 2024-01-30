# Authors: Based on https://github.com/ucl-pond/pySuStaIn/blob/master/setup.py 
# License: TBC
__version__ = '0.1'

from setuptools import setup

#parse the requirement.txt file, ignoring commented lines, placing results in install_reqs
with open('requirements.txt', 'r') as f:
    install_reqs = [
        s for s in [
            line.strip(' \n') for line in f
        ] if not s.startswith('#') and s != ''
    ]


print("Started SEPAL setup.py")

setup(name=               'SEPAL',
      version=            __version__,
      description=        'SEPAL',
      url=                'https://github.com/mjt320/SEPAL',
      classifiers=			  ['Intended Audience :: Science/Research',
                   			  'Programming Language :: Python',
                   			  'Topic :: Scientific/Engineering',
                   			  'Programming Language :: Python :: 3.7'],
      maintainer=         '',
      maintainer_email=   '',
      license=		        'TBC',
      packages=			      ['SEPAL','SEPAL_utils'],
      python_requires=  	'>=3.7',
      install_requires =  install_reqs,	#the parsed requirements from requirements.txt
      entry_points=			  {},
      zip_safe=				    False)

print("Finished SEPAL setup.py")
