import os
import sys

FOLDERS = [
    "data/pdfs",
    "data/chroma_db",
    "agents",
    "mcp_server",
    "ui",
]

INIT_FILES = [
    "agents/__init__.py",
    "mcp_server/__init__.py",
    "ui/__init__.py",
]


def create_folders():
    for folder in FOLDERS:
        os.makedirs(folder, exist_ok=True)
    print("Folders created.")


def create_init_files():
    for path in INIT_FILES:
        if not os.path.exists(path):
            open(path, "w").close()
    print("Package init files ready.")


def check_env():
    if not os.path.exists(".env"):
        print("ERROR: .env not found. Copy .env.example to .env and add your OPENAI_API_KEY.")
        return False
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith("sk-..."):
        print("ERROR: OPENAI_API_KEY is not set in .env")
        return False
    print("Environment OK.")
    return True


def check_imports():
    packages = {
        "langchain":             "langchain",
        "langchain_community":   "langchain-community",
        "langchain_openai":      "langchain-openai",
        "langgraph":             "langgraph",
        "chromadb":              "chromadb",
        "sentence_transformers": "sentence-transformers",
        "pypdf":                 "pypdf",
        "sqlalchemy":            "sqlalchemy",
        "mcp":                   "mcp",
        "streamlit":             "streamlit",
        "faker":                 "faker",
        "dotenv":                "python-dotenv",
    }
    missing = []
    for module, pip_name in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print("Missing packages:")
        for pkg in missing:
            print(f"  pip install {pkg}")
        return False

    print("All packages installed.")
    return True


def main():
    create_folders()
    create_init_files()
    env_ok     = check_env()
    imports_ok = check_imports()

    if env_ok and imports_ok:
        print("\nSetup complete. Next steps:")
        print("  1. Add Apple policy PDFs to data/pdfs/")
        print("  2. Run: python generate_apple_data.py")
        print("  3. Run: python rag_pipeline.py")
        print("  4. Run: streamlit run ui/app.py")
    else:
        print("\nFix the errors above and re-run setup_project.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
