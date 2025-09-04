"""
プロジェクト構造の検証テスト
"""
import os
import pytest
from pathlib import Path


class TestProjectStructure:
    """プロジェクト構造のテストクラス"""
    
    def test_src_data_layer_ディレクトリが存在する(self):
        """src/data_layer/ディレクトリが存在することを確認"""
        assert Path("src/data_layer").exists()
        assert Path("src/data_layer").is_dir()
    
    def test_src_business_layer_ディレクトリが存在する(self):
        """src/business_layer/ディレクトリが存在することを確認"""
        assert Path("src/business_layer").exists()
        assert Path("src/business_layer").is_dir()
    
    def test_src_presentation_layer_ディレクトリが存在する(self):
        """src/presentation_layer/ディレクトリが存在することを確認"""
        assert Path("src/presentation_layer").exists()
        assert Path("src/presentation_layer").is_dir()
    
    def test_tests_ディレクトリが存在する(self):
        """tests/ディレクトリが存在することを確認"""
        assert Path("tests").exists()
        assert Path("tests").is_dir()
    
    def test_logs_ディレクトリが存在する(self):
        """logs/ディレクトリが存在することを確認"""
        assert Path("logs").exists()
        assert Path("logs").is_dir()
    
    def test_data_ディレクトリが存在する(self):
        """data/ディレクトリが存在することを確認"""
        assert Path("data").exists()
        assert Path("data").is_dir()
    
    def test_output_ディレクトリが存在する(self):
        """output/ディレクトリが存在することを確認"""
        assert Path("output").exists()
        assert Path("output").is_dir()


class TestInitFiles:
    """__init__.pyファイルの存在テスト"""
    
    def test_src_init_pyが存在する(self):
        """src/__init__.pyが存在することを確認"""
        assert Path("src/__init__.py").exists()
        assert Path("src/__init__.py").is_file()
    
    def test_src_data_layer_init_pyが存在する(self):
        """src/data_layer/__init__.pyが存在することを確認"""
        assert Path("src/data_layer/__init__.py").exists()
        assert Path("src/data_layer/__init__.py").is_file()
    
    def test_src_business_layer_init_pyが存在する(self):
        """src/business_layer/__init__.pyが存在することを確認"""
        assert Path("src/business_layer/__init__.py").exists()
        assert Path("src/business_layer/__init__.py").is_file()
    
    def test_src_presentation_layer_init_pyが存在する(self):
        """src/presentation_layer/__init__.pyが存在することを確認"""
        assert Path("src/presentation_layer/__init__.py").exists()
        assert Path("src/presentation_layer/__init__.py").is_file()
    
    def test_tests_init_pyが存在する(self):
        """tests/__init__.pyが存在することを確認"""
        assert Path("tests/__init__.py").exists()
        assert Path("tests/__init__.py").is_file()


class TestConfigFiles:
    """設定ファイルの存在テスト"""
    
    def test_gitignoreが存在する(self):
        """.gitignoreファイルが存在することを確認"""
        assert Path(".gitignore").exists()
        assert Path(".gitignore").is_file()
    
    def test_gitignoreの内容が適切(self):
        """.gitignoreの内容が適切であることを確認"""
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Python関連の除外設定があることを確認
        assert "__pycache__" in content
        assert "*.py[cod]" in content
        assert ".env" in content
        assert "logs/" in content
        assert "data/" in content
        assert "*.db" in content
    
    def test_requirements_txtが存在する(self):
        """requirements.txtが存在することを確認"""
        assert Path("requirements.txt").exists()
        assert Path("requirements.txt").is_file()
    
    def test_env_exampleが存在する(self):
        """.env.exampleが存在することを確認"""
        assert Path(".env.example").exists()
        assert Path(".env.example").is_file()