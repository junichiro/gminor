"""設定ファイル読み込み機能のテスト"""
import os
import shutil
import tempfile
from pathlib import Path
import pytest
import yaml
from src.business_layer.config_loader import ConfigLoader, ConfigError


class TestConfigLoader:
    """ConfigLoaderのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前処理"""
        self.loader = ConfigLoader()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """各テストメソッドの後処理"""
        shutil.rmtree(self.temp_dir)

    def test_正常な設定ファイルを読み込める(self):
        """正常系: 有効なYAMLファイルを読み込めることを確認"""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "testdb"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(message)s"
            }
        }
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        result = self.loader.load_config(config_path)
        
        assert result == config_data
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["logging"]["level"] == "INFO"

    def test_存在しないファイルの場合エラーを発生させる(self):
        """異常系: 存在しないファイルを指定した場合、ConfigErrorが発生することを確認"""
        non_existent_path = os.path.join(self.temp_dir, "non_existent.yaml")
        
        with pytest.raises(ConfigError) as exc_info:
            self.loader.load_config(non_existent_path)
        
        assert "設定ファイルが見つかりません" in str(exc_info.value)

    def test_不正なYAML形式の場合エラーを発生させる(self):
        """異常系: 不正なYAML形式のファイルの場合、ConfigErrorが発生することを確認"""
        config_path = os.path.join(self.temp_dir, "invalid.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content:\n  - without proper: formatting")
        
        with pytest.raises(ConfigError) as exc_info:
            self.loader.load_config(config_path)
        
        assert "設定ファイルの形式が不正です" in str(exc_info.value)

    def test_空のファイルの場合エラーを発生させる(self):
        """異常系: 空のファイルの場合、ConfigErrorが発生することを確認"""
        config_path = os.path.join(self.temp_dir, "empty.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("")
        
        with pytest.raises(ConfigError) as exc_info:
            self.loader.load_config(config_path)
        
        assert "設定ファイルが空です" in str(exc_info.value)

    def test_デフォルト値を適用できる(self):
        """正常系: デフォルト値を設定できることを確認"""
        config_data = {
            "database": {
                "host": "localhost"
            }
        }
        
        config_path = os.path.join(self.temp_dir, "partial.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        defaults = {
            "database": {
                "port": 5432,
                "name": "defaultdb"
            },
            "logging": {
                "level": "WARNING"
            }
        }
        
        result = self.loader.load_config(config_path, defaults=defaults)
        
        assert result["database"]["host"] == "localhost"  # 設定ファイルの値
        assert result["database"]["port"] == 5432  # デフォルト値
        assert result["database"]["name"] == "defaultdb"  # デフォルト値
        assert result["logging"]["level"] == "WARNING"  # デフォルト値

    def test_相対パスを絶対パスに変換できる(self, monkeypatch):
        """正常系: 相対パスを指定した場合でも読み込めることを確認"""
        config_data = {"test": "value"}
        
        # monkeypatchを使用して安全にディレクトリを変更
        monkeypatch.chdir(self.temp_dir)
        
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        result = self.loader.load_config("config.yaml")
        assert result == config_data

    def test_設定値の検証機能が動作する(self):
        """正常系: バリデーション機能が正しく動作することを確認"""
        config_data = {
            "database": {
                "port": "invalid_port"  # 数値であるべき
            }
        }
        
        config_path = os.path.join(self.temp_dir, "invalid_value.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        # バリデーションルールを定義
        validation_rules = {
            "database.port": lambda x: isinstance(x, int) and 1 <= x <= 65535
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.loader.load_config(config_path, validation_rules=validation_rules)
        
        assert "設定値が不正です" in str(exc_info.value)