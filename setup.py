from setuptools import setup

setup(
    name="dcm-object-validator",
    description="flask app for object-validator-containers",
    author="LZV.nrw",
    install_requires=[
        "flask==3.*",
        "PyYAML==6.*",
        "requests==2.*",
        "dcm-object-validator-api>=1.0.0,<2",
        "lzvnrw-supplements>=1.8,<2",
        "dcm-bag-validator>=0.4,<1",
    ],
    packages=[
        "dcm_object_validator",
    ],
    package_data={
        "dcm_object_validator": [
            "dcm_object_validator/static/payload_profile.json",
        ],
    },
    include_package_data=True,
    setuptools_git_versioning={
          "enabled": True,
          "version_file": "VERSION",
          "count_commits_from_version_file": True,
          "dev_template": "{tag}.dev{ccount}",
    },
)
