from setuptools import setup

setup(
    version="5.2.0",
    name="dcm-object-validator",
    description="flask app implementing the DCM Object Validator API",
    author="LZV.nrw",
    license="MIT",
    python_requires=">=3.10",
    install_requires=[
        "flask==3.*",
        "PyYAML==6.*",
        "data-plumber-http>=1.0.0,<2",
        "dcm-object-validator-api>=5.0.0,<6",
        "dcm-common[services, db, orchestration]>=3.28.0,<4",
    ],
    packages=[
        "dcm_object_validator",
        "dcm_object_validator.models",
        "dcm_object_validator.plugins",
        "dcm_object_validator.plugins.identification",
        "dcm_object_validator.plugins.validation",
        "dcm_object_validator.views",
    ],
    package_data={},
    include_package_data=True,
    extras_require={
        "cors": ["Flask-CORS==4"],
        "fido": ["opf-fido>=1.6,<2"],
    },
    setuptools_git_versioning={
          "enabled": True,
          "version_file": "VERSION",
          "count_commits_from_version_file": True,
          "dev_template": "{tag}.dev{ccount}",
    },
)
