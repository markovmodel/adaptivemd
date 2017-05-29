"""Adaptive-MD
"""
from __future__ import print_function
from setuptools import setup
import sys

# experimental yaml support to read the settings
import yaml

sys.path.insert(0, '.')


def trunc_lines(s):
    parts = s.split('\n')
    while len(parts[0]) == 0:
        parts = parts[1:]

    while len(parts[-1]) == 0:
        parts = parts[:-1]

    parts = [part for part in parts if len(part) > 0]

    return ''.join(parts)

# +-----------------------------------------------------------------------------
# | CONSTRUCT PARAMETERS FOR setuptools
# +-----------------------------------------------------------------------------

def build_keyword_dictionary(prefs):
    keywords = {}

    for key in [
        'name', 'license', 'url', 'download_url', 'packages',
        'package_dir', 'platforms', 'description', 'install_requires',
        'long_description', 'package_data', 'include_package_data', 'scripts'
    ]:
        if key in prefs:
            keywords[key] = prefs[key]

    keywords['author'] = \
        ', '.join(prefs['authors'][:-1]) + ' and ' + \
        prefs['authors'][-1]

    keywords['author_email'] = \
        ', '.join(prefs['emails'])

    keywords["package_dir"] = \
        {package: '/'.join(package.split('.')) for package in prefs['packages']}

    keywords['long_description'] = \
        trunc_lines(keywords['long_description'])

    output = ""
    first_tab = 40
    second_tab = 60
    for key in sorted(keywords.keys()):
        value = keywords[key]
        output += key.rjust(first_tab) + str(value).rjust(second_tab) + ""

    return keywords


# load settings from setup.py, easier to maintain, but not fully supported yet
with open('setup.yaml') as f:
    yaml_string = ''.join(f.readlines())
    preferences = yaml.load(yaml_string)

print(preferences)

setup_keywords = build_keyword_dictionary(preferences)


if __name__ == '__main__':
    import versioneer
    setup(version=versioneer.get_version(),
          cmdclass=versioneer.get_cmdclass(),
          **setup_keywords)
