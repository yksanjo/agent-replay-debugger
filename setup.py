from setuptools import setup, find_packages

setup(
    name="agent-replay-debugger",
    version="0.1.0",
    description="Record, replay, and debug AI agent sessions",
    author="Yoshi Kondo",
    author_email="yksanjo@gmail.com",
    url="https://github.com/yksanjo/agent-replay-debugger",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "server": ["fastapi>=0.100.0", "uvicorn>=0.23.0"],
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.20.0"],
        "langchain": ["langchain>=0.1.0"],
    },
    entry_points={
        "console_scripts": [
            "agent-replay=agent_replay_debugger.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
