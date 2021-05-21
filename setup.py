from setuptools import setup

setup(
    name='BigCloudCountryProposalTool',
    version='1.0',
    py_modules=['bigcloud'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        bigcloud=bigcloud:cli
    '''
)
