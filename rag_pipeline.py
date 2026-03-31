import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PDF_DIR         = Path("data/pdfs")
CHROMA_DIR      = Path("data/chroma_db")
COLLECTION      = "apple_policies"
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 150
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def load_pdfs(pdf_dir):
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}")
        sys.exit(1)

    docs = []
    for path in pdf_files:
        loaded = PyPDFLoader(str(path)).load()
        for doc in loaded:
            doc.metadata["source_file"] = path.name
        docs.extend(loaded)
        print(f"  Loaded {path.name} ({len(loaded)} pages)")

    return docs


def chunk_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def build_vectorstore(chunks):
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=str(CHROMA_DIR),
    )


def smoke_test(vectorstore):
    queries = [
        "What is Apple's refund policy?",
        "How does Apple protect my personal data?",
        "What does AppleCare cover?",
    ]
    print("\nSmoke test:")
    for query in queries:
        results = vectorstore.similarity_search(query, k=1)
        if results:
            source  = results[0].metadata.get("source_file", "unknown")
            snippet = results[0].page_content[:100].replace("\n", " ")
            print(f"  [{source}] {snippet}...")
        else:
            print(f"  No results for: {query}")


def main():
    if not PDF_DIR.exists():
        print(f"PDF directory not found: {PDF_DIR}")
        sys.exit(1)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    if any(CHROMA_DIR.iterdir()):
        answer = input("ChromaDB already exists. Rebuild from scratch? [y/N]: ")
        if answer.strip().lower() != "y":
            embeddings  = OpenAIEmbeddings(model=EMBEDDING_MODEL)
            vectorstore = Chroma(
                collection_name=COLLECTION,
                embedding_function=embeddings,
                persist_directory=str(CHROMA_DIR),
            )
            smoke_test(vectorstore)
            return
        shutil.rmtree(CHROMA_DIR)
        CHROMA_DIR.mkdir()

    print("Loading PDFs...")
    docs   = load_pdfs(PDF_DIR)
    chunks = chunk_documents(docs)
    print(f"  {len(chunks)} chunks created")

    print("Embedding and storing in ChromaDB...")
    vectorstore = build_vectorstore(chunks)
    print(f"  Done. Stored at {CHROMA_DIR}/")

    smoke_test(vectorstore)


if __name__ == "__main__":
    main()
