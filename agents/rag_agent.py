import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.retrievers.multi_query import MultiQueryRetriever

load_dotenv()

CHROMA_DIR      = os.getenv("CHROMA_DIR", "data/chroma_db")
COLLECTION      = "apple_policies"
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
TOP_K           = 5

PROMPT_TEMPLATE = """You are a customer support policy assistant.
Use the excerpts below from Apple's official policy documents to answer the question.
Be specific and include relevant details such as time windows, fees, and conditions.

If the answer is not in the provided context, say:
"I could not find that information in the available Apple policy documents."
Do not infer or guess beyond what the documents state.

Context:
{context}

Question:
{question}

Answer:"""


def build_rag_agent():
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    vectorstore = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    retriever = MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(search_kwargs={"k": TOP_K}),
        llm=llm,
    )
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def run_rag_agent(query):
    result  = build_rag_agent().invoke({"query": query})
    answer  = result.get("result", "No answer returned.")
    sources = list({
        doc.metadata.get("source_file", "unknown")
        for doc in result.get("source_documents", [])
    })
    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    tests = [
        "What is Apple's return window for purchased products?",
        "What does AppleCare+ cover for accidental damage?",
        "Can I get a full refund if I cancel my AppleCare plan?",
    ]
    for q in tests:
        result = run_rag_agent(q)
        print(f"Q: {q}")
        print(f"A: {result['answer']}")
        print(f"   Sources: {', '.join(result['sources'])}\n")
