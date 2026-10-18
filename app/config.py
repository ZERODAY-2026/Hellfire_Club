"""
Dataset configuration loader for ThreatDesk.
Loads YAML configs and provides Pydantic models for configuration validation.
"""

import os
import yaml
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class ColumnConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: str
    description: str

class TableConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    description: str
    columns: Dict[str, ColumnConfig]

class ThreatIntelConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())
    database: str
    schema_name: str = Field(..., alias="schema")
    domain_name: Optional[str] = Field("Vulnerability Intelligence", description="Domain name")
    domain_persona: Optional[str] = Field("Expert security data analyst", description="Domain persona")
    allowed_tables: List[str]
    tables: Dict[str, TableConfig]

def get_config_path(config_name: str = None) -> str:
    root_dir = os.path.dirname(os.path.dirname(__file__))
    if not config_name:
        config_name = os.getenv("DATASET_CONFIG", "threat_intel.yaml")
    if not os.path.isabs(config_name):
        config_path = os.path.join(root_dir, "configs", config_name)
    else:
        config_path = config_name
    if not os.path.exists(config_path):
        config_path = os.path.join(root_dir, "configs", "threat_intel.yaml")
    return config_path

def load_config(config_path: str = None) -> ThreatIntelConfig:
    path = get_config_path(config_path)
    with open(path, 'r', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)

    env_db = os.getenv("SNOWFLAKE_DATABASE")
    env_schema = os.getenv("SNOWFLAKE_SCHEMA")

    if env_db and raw_data.get("database") == "THREAT_DB":
        raw_data["database"] = env_db
    if env_schema and raw_data.get("schema") == "THREAT_SCHEMA":
        raw_data["schema"] = env_schema

    return ThreatIntelConfig(**raw_data)
