from distutils.core import setup

setup(name = 'geotz',
      version = '1.0rc',
      author = 'Barron Henderson',
      author_email = 'barronh@gmail.com',
      maintainer = 'Barron Henderson',
      maintainer_email = 'barronh@gmail.com',
      packages = ['geotz'],
      package_dir = {'geotz': 'src/geotz'},
      package_data = {'geotz': ['*.pkl', '*.txt']},
      requires = ['shapely']
      )
