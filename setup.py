from setuptools import setup, find_packages

setup(
    name='GA_SNS_Simulation',
    version='1.0',
    packages=find_packages(),
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'sns-simulation=sns_simulation.main:main',
        ],
    },
    author='Hyeonseo Yun',
    author_email='0525yhs@gmail.com',
    description='A simulation of social networking service activities.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/0525hhgus/GA_SNS_Simulation',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)