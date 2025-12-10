"""
LoRA Training Tool Setup
Package setup for installation and distribution.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="lora-training-tool",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive tool for training LoRA models on Stable Diffusion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/AI-Assistant",
    packages=find_packages(include=['utils', 'utils.*', 'src', 'src.*', 'config', 'config.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "notebooks": [
            "jupyter>=1.0.0",
            "notebook>=6.4.0",
            "ipywidgets>=7.6.0",
            "matplotlib>=3.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lora-train=scripts.training.train_lora:main",
            "lora-generate=scripts.utilities.generate_samples:main",
            "lora-analyze=scripts.utilities.analyze_lora:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.txt", "*.md"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/AI-Assistant/issues",
        "Source": "https://github.com/yourusername/AI-Assistant",
        "Documentation": "https://github.com/yourusername/AI-Assistant/tree/main/train_LoRA_tool/docs",
    },
)
