"""Configuration for the ADS-backed technosignature research RAG."""
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    ads_api_token: str = ""
    ads_query: str = "abs:(SETI OR Technosignature)"
    ads_database_filter: str = "database: astronomy"
    ads_rows_per_page: int = 500
    download_timeout_seconds: int = 45
    download_retries: int = 1
    download_workers: int = 8
    parser_workers: int = 2
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    generation_model: str = "qwen2.5:14b-instruct"
    rerank_model: str = ""
    rerank_revision: str = ""
    rerank_backend: Literal["ollama", "cross-encoder"] = "ollama"
    rerank_device: str = "cpu"
    rerank_batch_size: int = 8
    embedding_batch_size: int = 32
    vector_data_dir: Path = REPO_ROOT / "data"
    chunk_min_tokens: int = 300
    chunk_max_tokens: int = 750
    chunk_overlap_tokens: int = 90
    top_k: int = 10
    per_paper_limit: int = 3
    vector_index_metric: str = "cosine"
    rerank_enabled: bool = True
    rerank_pool_size: int = 40
    rerank_fetch_limit: int = 200
    visual_enabled: bool = True
    visual_embedding_model: str = "Qwen/Qwen3-VL-Embedding-2B"
    visual_embedding_revision: str = "9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda"
    visual_rerank_model: str = "Qwen/Qwen3-VL-Reranker-2B"
    visual_rerank_revision: str = "4bd860ac4f15ad1897a214615cccc700f8f71818"
    visual_device: str = "cuda"
    visual_embedding_dimensions: int = 2048
    visual_embedding_batch_size: int = 4
    visual_rerank_batch_size: int = 2
    visual_render_dpi: int = 120
    visual_jpeg_quality: int = 82
    visual_page_text_chars: int = 12000
    visual_embedding_prompt: str = "Retrieve scientific paper pages relevant to the user's technosignature research question."
    visual_rerank_prompt: str = "Retrieve scientific text or figures relevant to the user's technosignature research question."
    visual_base_url: str = "http://127.0.0.1:8000"
    mcp_transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_allowed_hosts: str = "127.0.0.1:8000,localhost:8000"
    mcp_allowed_origins: str = ""

    @property
    def pdf_dir(self) -> Path: return self.vector_data_dir / "pdfs"
    @property
    def metadata_dir(self) -> Path: return self.vector_data_dir / "metadata"
    @property
    def parsed_dir(self) -> Path: return self.vector_data_dir / "parsed"
    @property
    def chunks_dir(self) -> Path: return self.vector_data_dir / "chunks"
    @property
    def embeddings_cache_dir(self) -> Path: return self.vector_data_dir / "embeddings_cache"
    @property
    def lancedb_dir(self) -> Path: return self.vector_data_dir / "lancedb"
    @property
    def visual_pages_dir(self) -> Path: return self.vector_data_dir / "visual" / "pages"
    @property
    def visual_metadata_dir(self) -> Path: return self.vector_data_dir / "visual" / "metadata"
    @property
    def visual_embeddings_cache_dir(self) -> Path: return self.vector_data_dir / "visual" / "embeddings_cache"
    @property
    def visual_lancedb_dir(self) -> Path: return self.vector_data_dir / "visual" / "lancedb"
    @property
    def eval_dir(self) -> Path: return self.vector_data_dir / "eval"
    @property
    def research_dir(self) -> Path: return self.vector_data_dir / "research" / "technosignatures"
    @property
    def manifest_path(self) -> Path: return self.vector_data_dir / "manifest.sqlite3"

    @staticmethod
    def _csv_values(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def mcp_allowed_host_list(self) -> list[str]:
        return self._csv_values(self.mcp_allowed_hosts)

    @property
    def mcp_allowed_origin_list(self) -> list[str]:
        return self._csv_values(self.mcp_allowed_origins)

    def ensure_dirs(self) -> None:
        for directory in (self.pdf_dir, self.metadata_dir, self.parsed_dir, self.chunks_dir,
                          self.embeddings_cache_dir, self.lancedb_dir, self.eval_dir,
                          self.research_dir / "search", self.visual_pages_dir,
                          self.visual_metadata_dir, self.visual_embeddings_cache_dir,
                          self.visual_lancedb_dir):
            directory.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_dirs()
