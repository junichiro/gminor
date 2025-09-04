"""設定ファイル読み込みモジュール"""
import copy
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union
import yaml


class ConfigError(Exception):
    """設定関連のエラー"""
    pass


class ConfigLoader:
    """YAML設定ファイルを読み込むクラス"""
    
    def load_config(
        self, 
        config_path: Union[str, Path], 
        defaults: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[Dict[str, Callable]] = None
    ) -> Dict[str, Any]:
        """
        設定ファイルを読み込み、検証済み設定を返す
        
        Args:
            config_path: 設定ファイルのパス
            defaults: デフォルト設定値の辞書
            validation_rules: 検証ルールの辞書（キーパス: 検証関数）
            
        Returns:
            読み込んだ設定の辞書
            
        Raises:
            ConfigError: ファイルが見つからない、形式が不正、検証エラーなど
        """
        config_path = Path(config_path).resolve()
        
        self._validate_file_exists(config_path)
        config = self._load_yaml_file(config_path)
        
        if defaults:
            config = self._merge_defaults(defaults, config)
        
        if validation_rules:
            self._validate_config(config, validation_rules)
        
        return config
    
    def _validate_file_exists(self, config_path: Path) -> None:
        """ファイルの存在を確認する"""
        if not config_path.exists():
            raise ConfigError(f"設定ファイルが見つかりません: {config_path}")
    
    def _load_yaml_file(self, config_path: Path) -> Dict[str, Any]:
        """YAMLファイルを読み込む"""
        try:
            with config_path.open('r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
                if config is None:
                    raise ConfigError("設定ファイルが空です")
                    
                return config
                    
        except yaml.YAMLError as e:
            raise ConfigError(f"設定ファイルの形式が不正です: {e}")
        except Exception as e:
            if isinstance(e, ConfigError):
                raise
            raise ConfigError(f"設定ファイルの読み込みに失敗しました: {e}")
    
    def _merge_defaults(self, defaults: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """デフォルト値をマージする"""
        result = copy.deepcopy(defaults)
        
        def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        return deep_merge(result, config)
    
    def _validate_config(self, config: Dict[str, Any], rules: Dict[str, Callable]) -> None:
        """設定値を検証する"""
        for key_path, validator in rules.items():
            value = self._get_value_by_path(config, key_path)
            
            if not validator(value):
                raise ConfigError(f"設定値が不正です: {key_path} = {value}")
    
    def _get_value_by_path(self, config: Dict[str, Any], path: str) -> Any:
        """ドット区切りのパスから値を取得する"""
        keys = path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value