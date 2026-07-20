import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_PATH = os.path.join(BASE_DIR, "app", "core", "ml_config.json")
MODELS_DIR = os.path.join(BASE_DIR, "models")

class MLConfig:
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.history_years: int = 2
        self.start_year: int = 2024
        self.end_year: int = 2026
        self.db_engine: str = "sqlite"
        self.openaq_historical_stations: Dict[str, int] = {}
        self.openaq_v3_realtime_locations: Dict[str, int] = {}
        self.discovery: Dict[str, Any] = {}
        self.station_selection: Dict[str, Any] = {}

        
        # Training config
        self.seq_len: int = 72
        self.learning_rate: float = 0.001
        self.batch_size: int = 256
        self.epochs: int = 150
        self.patience: int = 25
        self.grad_clip: float = 1.0
        self.hidden_dim: int = 128
        self.num_lstm_layers: int = 3
        self.dropout: float = 0.35
        self.weight_decay: float = 5e-4
        self.warmup_epochs: int = 5
        self.huber_delta: float = 1.0
        self.k_neighbours: int = 3
        self.random_seed: int = 42
        
        self.load_config()

    def load_config(self) -> None:
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found at {self.config_path}. Using default settings.")
            return
        
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                
            # Parse Ingestion
            ingestion = data.get("ingestion", {})
            self.history_years = int(ingestion.get("history_years", self.history_years))
            self.start_year = int(ingestion.get("start_year", self.start_year))
            self.end_year = int(ingestion.get("end_year", self.end_year))
            self.db_engine = ingestion.get("db_engine", self.db_engine)
            self.openaq_historical_stations = ingestion.get("openaq_historical_stations", self.openaq_historical_stations)
            self.openaq_v3_realtime_locations = ingestion.get("openaq_v3_realtime_locations", self.openaq_v3_realtime_locations)
            self.discovery = ingestion.get("discovery", self.discovery)
            self.station_selection = data.get("station_selection", {})

            
            # Parse Training
            training = data.get("training", {})
            self.seq_len = int(training.get("seq_len", self.seq_len))
            self.learning_rate = float(training.get("learning_rate", self.learning_rate))
            self.batch_size = int(training.get("batch_size", self.batch_size))
            self.epochs = int(training.get("epochs", self.epochs))
            self.patience = int(training.get("patience", self.patience))
            self.grad_clip = float(training.get("grad_clip", self.grad_clip))
            self.hidden_dim = int(training.get("hidden_dim", self.hidden_dim))
            self.num_lstm_layers = int(training.get("num_lstm_layers", self.num_lstm_layers))
            self.dropout = float(training.get("dropout", self.dropout))
            self.weight_decay = float(training.get("weight_decay", self.weight_decay))
            self.warmup_epochs = int(training.get("warmup_epochs", self.warmup_epochs))
            self.huber_delta = float(training.get("huber_delta", self.huber_delta))
            self.k_neighbours = int(training.get("k_neighbours", self.k_neighbours))
            self.random_seed = int(training.get("random_seed", self.random_seed))
            
            logger.info(f"Successfully loaded ML config from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {self.config_path}: {e}. Using defaults.")

# Global config instance
config = MLConfig()
