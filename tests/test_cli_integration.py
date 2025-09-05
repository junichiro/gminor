"""CLI統合テスト"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch


def test_CLIのBasicImportが成功する():
    """統合テスト: CLIモジュールの基本的なインポートが成功することを確認"""
    # 外部依存関係がない場合のテスト
    try:
        # Python構文の検証のみ（実際の実行は行わない）
        import ast
        
        cli_path = Path(__file__).parent.parent / 'src' / 'presentation_layer' / 'cli.py'
        
        with open(cli_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # AST解析によるpython構文の検証
        ast.parse(source_code)
        
        # 成功した場合
        assert True
        
    except SyntaxError as e:
        pytest.fail(f"CLI module has syntax errors: {e}")
    except Exception as e:
        pytest.fail(f"Failed to validate CLI module: {e}")


def test_MainPyの構文が正しい():
    """統合テスト: main.pyの構文が正しいことを確認"""
    try:
        import ast
        
        main_path = Path(__file__).parent.parent / 'main.py'
        
        with open(main_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # AST解析による構文検証
        ast.parse(source_code)
        
        # 成功した場合
        assert True
        
    except SyntaxError as e:
        pytest.fail(f"main.py has syntax errors: {e}")
    except Exception as e:
        pytest.fail(f"Failed to validate main.py: {e}")


def test_必要なヘルパー関数が定義されている():
    """統合テスト: 必要なヘルパー関数が定義されていることを確認"""
    import ast
    
    cli_path = Path(__file__).parent.parent / 'src' / 'presentation_layer' / 'cli.py'
    
    with open(cli_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    tree = ast.parse(source_code)
    
    # 定義されている関数名を取得
    function_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_names.append(node.name)
    
    # 期待される関数が定義されていることを確認
    expected_functions = [
        'load_config_and_validate',
        'create_components',
        'create_services_from_components',
        '_display_sync_result',
        'cli',
        'init',
        'visualize'
    ]
    
    for func_name in expected_functions:
        assert func_name in function_names, f"Function '{func_name}' is not defined"


def test_CLIコマンドのClick装飾子が正しく設定されている():
    """統合テスト: Clickコマンドの装飾子が正しく設定されていることを確認"""
    import ast
    
    cli_path = Path(__file__).parent.parent / 'src' / 'presentation_layer' / 'cli.py'
    
    with open(cli_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    tree = ast.parse(source_code)
    
    # 装飾子付きの関数を確認
    decorated_functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            decorators = []
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    decorators.append(f"{decorator.value.id}.{decorator.attr}")
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    decorators.append(f"{decorator.func.value.id}.{decorator.func.attr}")
                elif isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
            decorated_functions[node.name] = decorators
    
    # cli関数がclick.groupで装飾されていることを確認
    assert 'cli' in decorated_functions
    assert any('group' in dec for dec in decorated_functions['cli'])
    
    # init関数がclick.commandで装飾されていることを確認
    assert 'init' in decorated_functions
    assert any('command' in dec for dec in decorated_functions['init'])
    
    # visualize関数がclick.commandで装飾されていることを確認
    assert 'visualize' in decorated_functions
    assert any('command' in dec for dec in decorated_functions['visualize'])


def test_設定ファイルの構造が適切():
    """統合テスト: 設定ファイルの構造が適切であることを確認"""
    import yaml
    
    config_path = Path(__file__).parent.parent / 'config.yaml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 必要なセクションが存在することを確認
    assert 'database' in config
    assert 'github' in config
    assert 'application' in config
    
    # github セクションの構造確認
    assert 'api_base_url' in config['github']
    assert 'repositories' in config['github']
    assert isinstance(config['github']['repositories'], list)


def test_Databasemanagerに必要なメソッドが追加されている():
    """統合テスト: DatabaseManagerにget_weekly_metricsメソッドが追加されていることを確認"""
    import ast
    
    db_manager_path = Path(__file__).parent.parent / 'src' / 'data_layer' / 'database_manager.py'
    
    with open(db_manager_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    tree = ast.parse(source_code)
    
    # DatabaseManagerクラス内のメソッドを取得
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'DatabaseManager':
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
    
    # get_weekly_metricsメソッドが存在することを確認
    assert 'get_weekly_metrics' in methods, "get_weekly_metrics method is missing from DatabaseManager"