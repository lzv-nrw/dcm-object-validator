from setuptools import setup

setup(
    version="4.0.1",
    name="dcm-object-validator",
    description="flask app implementing the DCM Object Validator API",
    author="LZV.nrw",
    license="MIT",
    python_requires=">=3.10",
    install_requires=[
        "flask==3.*",
        "PyYAML==6.*",
        "requests==2.*",
        "data-plumber-http>=1.0.0,<2",
        "dcm-object-validator-api>=4.1.0,<5",
        "dcm-common[services, db, orchestration]>=3.11.0,<4",
        "dcm-bag-validator>=2.0.0,<3",
    ],
    packages=[
        "dcm_object_validator",
        "dcm_object_validator.models",
        "dcm_object_validator.views",
    ],
    package_data={
        "dcm_object_validator": [
            "dcm_object_validator/static/payload_profile.json",
            "py.typed",
        ],
    },
    include_package_data=True,
    extras_require={
        "cors": ["Flask-CORS==4"],
    },
    setuptools_git_versioning={
          "enabled": True,
          "version_file": "VERSION",
          "count_commits_from_version_file": True,
          "dev_template": "{tag}.dev{ccount}",
    },
)
