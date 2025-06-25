# 在适当的位置创建文件，例如 common/parsers.py
import json
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError

class PlainTextJSONParser(BaseParser):
    """
    自定义解析器：将 text/plain 内容解析为 JSON
    """
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        解析 text/plain 内容为 JSON 对象
        """
        try:
            # 读取并解码文本内容
            text = stream.read().decode('utf-8')

            # 尝试解析为JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                # 提供更详细的错误信息
                raise ParseError(f'Invalid JSON: {str(e)}')
        except UnicodeDecodeError:
            raise ParseError('Invalid text encoding')
        except Exception as e:
            raise ParseError(f'Parse error: {str(e)}')