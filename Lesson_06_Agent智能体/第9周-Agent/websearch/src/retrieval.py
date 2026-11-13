import yaml
import os
from .fetch_web_content import WebContentFetcher
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.utils import embedding_functions
import chromadb
chroma_client = chromadb.Client()







class EmbeddingRetriever:
    TOP_K = 20  # Number of top K documents to retrieve

    def __init__(self):
        # Load configuration from config.yaml file
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)

        # Initialize the text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=0
        )
        


    def retrievel_embeddings(self, contents_list: list, link_list: list, query: str):
        # Retrieve embeddings for a given list of contents and a query
        metadatas = [{'url': link} for link in link_list]
        texts = self.text_splitter.create_documents(contents_list, metadatas=metadatas)

        # Create a Chroma database from the documents using specific embeddings
        
        embedding = SentenceTransformerEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
        


        db = Chroma.from_documents(
            documents=texts,
            embedding=embedding
        )


        # Create a retriever from the database to find relevant documents
        retriever = db.as_retriever(search_kwargs={"k": min(self.TOP_K,len(texts))})
        return retriever.get_relevant_documents(query) # Retrieve and return the relevant documents


def web_retrieval(query):
    web_contents_fetcher = WebContentFetcher(query)
    web_contents, serper_response = web_contents_fetcher.fetch()

    retriever = EmbeddingRetriever()
    relevant_docs_list = retriever.retrievel_embeddings(web_contents, serper_response['links'], query)
    return relevant_docs_list   

# Example usage
if __name__ == "__main__":
    query = "介绍一下小米汽车"


    relevant_docs_list = web_retrieval(query)

    print("\n\nRelevant Documents from VectorDB:\n", relevant_docs_list)
    