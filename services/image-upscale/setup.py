from setuptools import setup, find_packages
import os

# Read README
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "Image upscaling tool using Real-ESRGAN and other models"

# Read requirements
req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(req_path):
    with open(req_path, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    requirements = [
        "torch>=1.7.0",
        "torchvision>=0.8.0",
        "numpy>=1.20.0",
        "pillow>=8.0.0",
        "basicsr>=1.4.2",
        "realesrgan>=0.3.0",
        "tqdm>=4.60.0",
        "pyyaml>=5.4.0",
        "requests>=2.25.0",
    ]

setup(
    name="upscale-tool",
    version="1.0.0",
    author="AI-Assistant Team",
    author_email="",
    description="Image upscaling tool using Real-ESRGAN and other models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SkastVnT/AI-Assistant",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Graphics",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
        ],
        "web": [
            "gradio>=3.0.0",
            "fastapi>=0.95.0",
            "uvicorn>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "upscale-tool=upscale_tool.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
