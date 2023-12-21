import re
import sys
from distutils.errors import DistutilsFileError
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class PostBuildExtCommand(build_ext):
    """Post-installation for extension."""

    def run(self):
        rad_path = Path(__file__).parent / "src"
        sys.path.append(str(rad_path))

        from rad.pydantic.generator import setup_files

        setup_files()
        try:
            build_ext.run(self)
        except DistutilsFileError as err:
            if (
                re.match(r"can't copy '.*/rad/pydantic/_generated[.]cpython.*: doesn't exist or not a regular file.*", str(err))
                is None
            ):
                raise err


setup(
    cmdclass={
        "build_ext": PostBuildExtCommand,
    },
    ext_modules=[
        Extension(
            "rad.pydantic._generated",
            [],
        ),
    ],
)
