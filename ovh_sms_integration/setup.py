from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="ovh_sms_integration",
    version="1.0.0",
    description="Intégration SMS OVH pour ERPNext",
    author="Votre Organisation",
    author_email="admin@votre-domaine.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)