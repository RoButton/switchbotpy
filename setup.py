from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='switchbotpy',
    packages=['switchbotpy'],
    version='0.1.6',
    license='MIT',
    description='An API for Switchbots that allows to control actions, settings and timers (also password protected)',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Nicolas Küchler',
    author_email='nico.kuechler@protonmail.com',
    url='https://github.com/RoButton/switchbotpy',
    download_url='https://github.com/RoButton/switchbotpy/archive/v_016.tar.gz',
    keywords=['Switchbot', 'Ble', 'Button', 'Actions', 'Settings', 'Timers'],
    install_requires=['pygatt', 'pexpect'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
