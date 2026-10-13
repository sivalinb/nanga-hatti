import os
from dataclasses import dataclass, field
from pathlib import Path

def secret(name, file_name):
    value=os.getenv(name,"").strip()
    if value: return value
    path=os.getenv(file_name,"")
    return Path(path).read_text().strip() if path else ""

@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda:Path(os.getenv("NANGA_DATA_DIR","data/private")))
    live: bool = field(default_factory=lambda:os.getenv("NANGA_LIVE_AI","0")=="1")
    llm_key: str = field(default_factory=lambda:secret("NEBIUS_API_KEY","NANGA_LLM_KEY_FILE"),repr=False)
    braintrust_key: str = field(default_factory=lambda:secret("BRAINTRUST_API_KEY","NANGA_BRAINTRUST_KEY_FILE"),repr=False)
    server_token: str = field(default_factory=lambda:os.getenv("NANGA_SERVER_TOKEN",""),repr=False)
    trusted_network: str = field(default_factory=lambda:os.getenv("NANGA_TRUSTED_NETWORK",""))
    base_url: str = field(default_factory=lambda:os.getenv("NANGA_LLM_BASE_URL","https://api.studio.nebius.com/v1"))
    model: str = field(default_factory=lambda:os.getenv("NANGA_LLM_MODEL","Qwen/Qwen3-30B-A3B-Instruct-2507"))
    braintrust_project: str = field(default_factory=lambda:os.getenv("NANGA_BRAINTRUST_PROJECT","Nanga Hatti"))
    input_price: float | None = field(default_factory=lambda:float(os.environ["NANGA_INPUT_USD_PER_MILLION"]) if os.getenv("NANGA_INPUT_USD_PER_MILLION") else None)
    output_price: float | None = field(default_factory=lambda:float(os.environ["NANGA_OUTPUT_USD_PER_MILLION"]) if os.getenv("NANGA_OUTPUT_USD_PER_MILLION") else None)
    max_searches: int = 2
    timeout: float = 40.0
